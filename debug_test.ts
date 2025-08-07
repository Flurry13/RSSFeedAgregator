import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';

dotenv.config();

const HF_API_KEY = process.env.HF_API_KEY;

if (!HF_API_KEY) {
    console.error('❌ HF_API_KEY environment variable is required');
    process.exit(1);
}

const client = new InferenceClient(HF_API_KEY);

// Test dataset for debugging
const testHeadlines = [
    "Trump Announces New Trade Deal with China",
    "Scientists Discover New Species in Amazon Rainforest",
    "Tech Giant Reports Record Quarterly Profits"
];

// Candidate topics for classification
const candidateTopics = [
    'politics', 'economy', 'technology', 'science', 'health', 'environment',
    'sports', 'entertainment', 'lifestyle', 'world', 'local', 'business',
    'education', 'travel', 'food', 'fashion', 'art'
];

// Single classification function with debugger statements
async function classifySingle(text: string) {
    console.log(`🔍 Classifying: "${text}"`);
    
    // Debugger statement - execution will pause here when debugging
    debugger;
    
    try {
        console.log(`  📡 Making API call to Hugging Face...`);
        
        // Another debugger point to inspect the API call
        debugger;
        
        const result = await client.zeroShotClassification({
            model: "facebook/bart-large-mnli",
            inputs: text,
            parameters: {
                candidate_labels: candidateTopics,
                multi_label: true,
            },
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
        
        // Debugger point to inspect the classification result
        debugger;
        
        console.log(`  🏷️  Top topics: ${classification.topTopics.map(t => `${t.topic} (${(t.confidence * 100).toFixed(1)}%)`).join(', ')}`);
        
        return classification;
    } catch (error: any) {
        console.error(`  ❌ Classification failed:`, error.message);
        
        // Debugger point for error handling
        debugger;
        
        return {
            text,
            topics: ['general'],
            scores: [1.0],
            topTopics: [{ topic: 'general', confidence: 1.0 }],
        };
    }
}

// Main test function
async function runDebugTest() {
    console.log('🧪 TypeScript Debug Test');
    console.log('========================');
    console.log(`📝 Test dataset: ${testHeadlines.length} headlines`);
    console.log(`🔑 API Key: ${HF_API_KEY ? '✅ Configured' : '❌ Missing'}`);
    
    // Debugger point at the start
    debugger;
    
    const results = [];
    
    for (let i = 0; i < testHeadlines.length; i++) {
        const headline = testHeadlines[i];
        console.log(`\n🔄 Processing headline ${i + 1}/${testHeadlines.length}`);
        
        // Debugger point before each classification
        debugger;
        
        const result = await classifySingle(headline);
        results.push(result);
        
        console.log(`   ✅ Completed: ${result.topTopics[0]?.topic || 'general'}`);
    }
    
    console.log('\n🎉 Debug test completed!');
    console.log(`   📊 Results: ${results.length} headlines processed`);
    
    // Final debugger point
    debugger;
    
    return results;
}

// Run the test
runDebugTest().catch(console.error); 