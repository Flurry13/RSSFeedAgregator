import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';

dotenv.config();

const HF_API_KEY = process.env.HF_API_KEY;

if (!HF_API_KEY) {
    console.error('❌ HF_API_KEY environment variable is required');
    process.exit(1);
}

const client = new InferenceClient(HF_API_KEY);

// Test dataset of 20 headlines
const testHeadlines = [
    "Trump Announces New Trade Deal with China",
    "Scientists Discover New Species in Amazon Rainforest",
    "Tech Giant Reports Record Quarterly Profits",
    "Global Climate Summit Reaches Historic Agreement",
    "Olympic Athlete Breaks World Record in Swimming",
    "New Medical Breakthrough Shows Promise for Cancer Treatment",
    "Stock Market Reaches All-Time High Amid Economic Recovery",
    "Space Mission Successfully Lands on Mars",
    "Major Film Studio Announces Blockbuster Sequel",
    "International Peace Talks Begin in Middle East",
    "Renewable Energy Surpasses Fossil Fuels for First Time",
    "Famous Chef Opens Revolutionary Restaurant Concept",
    "Cybersecurity Experts Warn of New Digital Threats",
    "Art Exhibition Draws Record Crowds in Paris",
    "Sports Team Wins Championship After Dramatic Final",
    "Educational Reform Bill Passes in Congress",
    "Travel Industry Bounces Back with Record Bookings",
    "Local Community Celebrates Cultural Festival",
    "Environmental Activists Protest Climate Inaction",
    "Fashion Designer Launches Sustainable Clothing Line"
];

// Candidate topics for classification
const candidateTopics = [
    'politics',
    'economy', 
    'technology',
    'science',
    'environment',
    'entertainment',
    'world',
    'business',
    'education',
    'art'
];

// Single classification function
async function classifySingle(text) {
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
            topics: result.map((r) => r.label),
            scores: result.map((r) => r.score),
            topTopics: result.slice(0, 3).map((r) => ({
                topic: r.label,
                confidence: r.score,
            })),
        };
        
        console.log(`  🏷️  Top topics: ${classification.topTopics.map(t => `${t.topic} (${(t.confidence * 100).toFixed(1)}%)`).join(', ')}`);
        
        return classification;
    } catch (error) {
        console.error(`  ❌ Classification failed:`, error.message);
        
        // Try fallback to Together AI if Groq fails
        if (error.message.includes('groq')) {
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
                    topics: fallbackResult.map((r) => r.label),
                    scores: fallbackResult.map((r) => r.score),
                    topTopics: fallbackResult.slice(0, 3).map((r) => ({
                        topic: r.label,
                        confidence: r.score,
                    })),
                };
                
                console.log(`  🏷️  Top topics: ${fallbackClassification.topTopics.map(t => `${t.topic} (${(t.confidence * 100).toFixed(1)}%)`).join(', ')}`);
                
                return fallbackClassification;
            } catch (fallbackError) {
                console.error(`  ❌ Fallback also failed:`, fallbackError.message);
            }
        }
        
        return {
            text,
            topics: ['general'],
            scores: [1.0],
            topTopics: [{ topic: 'general', confidence: 1.0 }],
        };
    }
}

// Test different concurrency levels
async function testConcurrency(concurrencyLevel) {
    console.log(`\n🚀 Testing with concurrency level: ${concurrencyLevel}`);
    console.log(`   📊 Processing ${testHeadlines.length} headlines with ${concurrencyLevel} concurrent requests`);
    
    const startTime = Date.now();
    
    // Process headlines in batches based on concurrency level
    const results = [];
    for (let i = 0; i < testHeadlines.length; i += concurrencyLevel) {
        const batch = testHeadlines.slice(i, i + concurrencyLevel);
        console.log(`\n🔄 Processing batch ${Math.floor(i / concurrencyLevel) + 1}/${Math.ceil(testHeadlines.length / concurrencyLevel)} (${batch.length} texts)`);
        
        const batchPromises = batch.map(text => classifySingle(text));
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
        
        console.log(`   ✅ Batch completed. Progress: ${results.length}/${testHeadlines.length} (${((results.length / testHeadlines.length) * 100).toFixed(1)}%)`);
    }
    
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    const throughput = (results.length / (totalTime / 1000)).toFixed(1);
    
    console.log(`\n🎉 Test completed!`);
    console.log(`   📊 Results for concurrency level ${concurrencyLevel}:`);
    console.log(`      - Total texts processed: ${results.length}`);
    console.log(`      - Total time: ${totalTime}ms`);
    console.log(`      - Success rate: ${((results.filter(r => r.topics[0] !== 'general').length / results.length) * 100).toFixed(1)}%`);
    console.log(`      - Average throughput: ${throughput} requests/second`);
    
    return { concurrencyLevel, totalTime, throughput, results };
}

// Test provider availability
async function testProviders() {
    console.log('\n🔍 Testing Provider Availability');
    console.log('================================');
    
    const providers = ['groq', 'together', 'fireworks', 'hf-inference'];
    const testText = "Test headline for provider check";
    
    // Test 1: Try with BART model (classification)
    console.log('\n📊 Test 1: BART Classification Model');
    for (const provider of providers) {
        console.log(`\n🧪 Testing ${provider} with BART model:`);
        try {
            const result = await client.zeroShotClassification({
                model: "facebook/bart-large-mnli",
                inputs: testText,
                parameters: {
                    candidate_labels: ['test'],
                    multi_label: false,
                },
                options: {
                    provider: provider
                }
            });
            console.log(`   ✅ ${provider}: SUCCESS`);
        } catch (error) {
            console.log(`   ❌ ${provider}: FAILED - ${error.message}`);
        }
    }
    
    // Test 2: Try with a Groq-compatible model (text generation)
    console.log('\n📊 Test 2: Groq-Compatible Models');
    const groqModels = [
        "meta-llama/Llama-2-7b-chat-hf",
        "microsoft/DialoGPT-medium",
        "gpt2"
    ];
    
    for (const model of groqModels) {
        console.log(`\n🧪 Testing Groq with ${model}:`);
        try {
            const result = await client.textGeneration({
                model: model,
                inputs: "Hello, how are you?",
                parameters: {
                    max_new_tokens: 10
                },
                options: {
                    provider: "groq"
                }
            });
            console.log(`   ✅ ${model}: SUCCESS`);
        } catch (error) {
            console.log(`   ❌ ${model}: FAILED - ${error.message}`);
        }
    }
}

// Main test function
async function runTests() {
    console.log('🧪 Hugging Face API Test Suite');
    console.log('================================');
    console.log(`📝 Test dataset: ${testHeadlines.length} headlines`);
    console.log(`🔑 API Key: ${HF_API_KEY ? '✅ Configured' : '❌ Missing'}`);
    
    // First test provider availability
    await testProviders();
    
    const testResults = [];
    
    // Test different concurrency levels
    const concurrencyLevels = [1, 3, 5, 10];
    
    for (const level of concurrencyLevels) {
        const result = await testConcurrency(level);
        testResults.push(result);
        
        // Add delay between tests to avoid rate limiting
        if (level !== concurrencyLevels[concurrencyLevels.length - 1]) {
            console.log(`\n⏳ Waiting 5 seconds before next test...`);
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
    
    // Summary
    console.log('\n📊 TEST SUMMARY');
    console.log('===============');
    testResults.forEach(result => {
        console.log(`Concurrency ${result.concurrencyLevel}: ${result.throughput} req/s (${result.totalTime}ms)`);
    });
    
    // Find best performing configuration
    const bestResult = testResults.reduce((best, current) => 
        parseFloat(current.throughput) > parseFloat(best.throughput) ? current : best
    );
    
    console.log(`\n🏆 Best performance: Concurrency ${bestResult.concurrencyLevel} with ${bestResult.throughput} requests/second`);
}

// Run the tests
runTests().catch(console.error); 