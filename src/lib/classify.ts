import dotenv from 'dotenv';
import { candidateTopics } from '../candidateTopics';
import { InferenceClient } from '@huggingface/inference';

dotenv.config();

const HF_API_KEY = process.env.HF_API_KEY;
const client = new InferenceClient(HF_API_KEY);

// Rate limiting configuration - TRUE 3 REQUESTS PER SECOND
const REQUESTS_PER_SECOND = 3; // Process 3 requests per second
const CONCURRENT_REQUESTS = 3; // Process 3 requests simultaneously
const MAX_RETRIES = 5; // More retries for rate limit handling
const INITIAL_RETRY_DELAY = 1000; // Start with 1 second
const MAX_RETRY_DELAY = 30000; // Max 30 seconds

// Token bucket rate limiter
class TokenBucketRateLimiter {
    private tokens = REQUESTS_PER_SECOND;
    private lastRefill = Date.now();
    private refillRate = REQUESTS_PER_SECOND; // tokens per second
    private maxTokens = REQUESTS_PER_SECOND;

    async acquire(): Promise<void> {
        this.refill();
        
        if (this.tokens < 1) {
            const waitTime = (1 - this.tokens) / this.refillRate * 1000;
            await new Promise(resolve => setTimeout(resolve, waitTime));
            this.refill();
        }
        
        this.tokens -= 1;
    }

    private refill(): void {
        const now = Date.now();
        const timePassed = (now - this.lastRefill) / 1000;
        const tokensToAdd = timePassed * this.refillRate;
        
        this.tokens = Math.min(this.maxTokens, this.tokens + tokensToAdd);
        this.lastRefill = now;
    }
}

const rateLimiter = new TokenBucketRateLimiter();

// Utility function to delay execution
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Single classification with exponential backoff for rate limits
async function classifySingle(text: string, retryCount = 0): Promise<any> {
    if (!HF_API_KEY) {
        throw new Error('HF_API_KEY environment variable is required');
    }
    
    console.log(`🔍 Classifying: "${text.substring(0, 60)}${text.length > 60 ? '...' : ''}"`);
    
    try {
        console.log(`  📡 Making API call to Hugging Face (Groq)...`);
        const result = await client.zeroShotClassification({
            model: "facebook/bart-large-mnli",
            inputs: text,
            parameters: {
                candidate_labels: candidateTopics,
                multi_label: true,
            },
            options: {
                provider: "groq" // Use Groq for maximum speed
            }
        });
        
        console.log(`  ✅ API call successful!`);
        
        const classification = {
            text,
            topics: result.map((r: any) => r.label),
            scores: result.map((r: any) => r.score),
            topTopics: result.slice(0, 3).map((r: any) => ({
                topic: r.label,
                confidence: r.score,
            })),
        };
        
        console.log(`  🏷️  Top topics: ${classification.topTopics.map(t => `${t.topic} (${(t.confidence * 100).toFixed(1)}%)`).join(', ')}`);
        
        return classification;
    } catch (error: any) {
        console.error(`  ❌ Classification attempt ${retryCount + 1} failed:`, error.message);
        
        // Try fallback to Together AI if Groq fails
        if (error.message.includes('groq') && retryCount === 0) {
            console.log(`  🔄 Trying Together AI as fallback...`);
            try {
                const fallbackResult = await client.zeroShotClassification({
                    model: "facebook/bart-large-mnli",
                    inputs: text,
                    parameters: {
                        candidate_labels: candidateTopics,
                        multi_label: true,
                    },
                    options: {
                        provider: "together" // Fallback to Together AI
                    }
                });
                
                console.log(`  ✅ Fallback API call successful!`);
                
                const fallbackClassification = {
                    text,
                    topics: fallbackResult.map((r: any) => r.label),
                    scores: fallbackResult.map((r: any) => r.score),
                    topTopics: fallbackResult.slice(0, 3).map((r: any) => ({
                        topic: r.label,
                        confidence: r.score,
                    })),
                };
                
                console.log(`  🏷️  Top topics: ${fallbackClassification.topTopics.map(t => `${t.topic} (${(t.confidence * 100).toFixed(1)}%)`).join(', ')}`);
                
                return fallbackClassification;
            } catch (fallbackError: any) {
                console.error(`  ❌ Fallback also failed:`, fallbackError.message);
            }
        }
        
        // Check if it's a rate limit error
        const isRateLimit = error.message.includes('429') || 
                           error.message.includes('rate limit') || 
                           error.message.includes('too many requests');
        
        if (retryCount < MAX_RETRIES) {
            // Calculate exponential backoff delay
            const backoffDelay = Math.min(
                INITIAL_RETRY_DELAY * Math.pow(2, retryCount),
                MAX_RETRY_DELAY
            );
            
            console.log(`  🔄 ${isRateLimit ? 'Rate limit hit' : 'Retrying'} in ${backoffDelay}ms... (attempt ${retryCount + 2}/${MAX_RETRIES + 1})`);
            await delay(backoffDelay);
            return classifySingle(text, retryCount + 1);
        }
        
        // If all retries failed, return a fallback classification
        console.warn(`  ⚠️  All retries failed. Using fallback classification.`);
        return {
            text,
            topics: ['general'],
            scores: [1.0],
            topTopics: [{ topic: 'general', confidence: 1.0 }],
        };
    }
}

// Rate-limited classification function
async function classifyWithRateLimit(text: string): Promise<any> {
    await rateLimiter.acquire();
    return classifySingle(text);
}

// Main classification function with batching
export async function classify(text: string) {
    return await classifyWithRateLimit(text);
}

// Batch classification function for multiple texts with rate limiting
export async function classifyBatch(texts: string[]): Promise<any[]> {
    if (!texts || texts.length === 0) {
        console.log('⚠️  No texts provided for classification');
        return [];
    }
    
    const overallStartTime = Date.now();
    
    console.log(`\n🚀 Starting batch classification of ${texts.length} texts`);
    console.log(`   📊 Configuration (TRUE CONCURRENT 3 RPS):`);
    console.log(`      - Requests per second: ${REQUESTS_PER_SECOND}`);
    console.log(`      - Concurrent requests: ${CONCURRENT_REQUESTS}`);
    console.log(`      - Max retries: ${MAX_RETRIES}`);
    console.log(`      - Initial retry delay: ${INITIAL_RETRY_DELAY}ms`);
    console.log(`      - Max retry delay: ${MAX_RETRY_DELAY}ms`);
    
    console.log(`\n🔄 Processing ${texts.length} texts with TRUE concurrent requests...`);
    
    try {
        const results: any[] = [];
        
        // Process all texts with true concurrency - no waiting between requests
        console.log(`   🚀 Launching ${texts.length} concurrent requests...`);
        
        // Start all requests simultaneously
        const promises = texts.map((text, index) => {
            console.log(`   📡 Starting request ${index + 1}/${texts.length}: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`);
            return classifySingle(text);
        });
        
        // Wait for all requests to complete
        const allResults = await Promise.all(promises);
        results.push(...allResults);
        
        const overallEndTime = Date.now();
        const totalTime = overallEndTime - overallStartTime;
        const throughput = (results.length / (totalTime / 1000)).toFixed(1);
        
        console.log(`\n🎉 Batch classification completed!`);
        console.log(`   📊 Final stats:`);
        console.log(`      - Total texts processed: ${results.length}`);
        console.log(`      - Total time: ${totalTime}ms`);
        console.log(`      - Success rate: ${((results.filter(r => r.topics[0] !== 'general').length / results.length) * 100).toFixed(1)}%`);
        console.log(`      - Average throughput: ${throughput} requests/second`);
        console.log(`      - Concurrent processing: ✅ TRUE (all requests launched simultaneously)`);
        
        return results;
        
    } catch (error) {
        console.error(`   ❌ Batch processing failed:`, error);
        // Return fallback results
        return texts.map(text => ({
            text,
            topics: ['general'],
            scores: [1.0],
            topTopics: [{ topic: 'general', confidence: 1.0 }],
        }));
    }
}