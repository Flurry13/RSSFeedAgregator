import { classify } from './src/lib/classify';

async function testClassification() {
    try {
        console.log('Testing topic classification...');
        
        const testTexts = [
            'Apple announces new iPhone with advanced AI features',
            'Stock market reaches new highs as tech companies surge',
            'Scientists discover new species in Amazon rainforest',
            'Local team wins championship in dramatic overtime victory'
        ];

        for (const text of testTexts) {
            console.log(`\nClassifying: "${text}"`);
            const result = await classify(text);
            console.log('Result:', JSON.stringify(result, null, 2));
        }
    } catch (error) {
        console.error('Test failed:', error);
    }
}

testClassification(); 