import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';
import { candidateTopics } from '../candidateTopics';

dotenv.config();

const HF_API_KEY = process.env.HF_API_KEY;

export async function classify(text: string) {
    if (!HF_API_KEY) {
        throw new Error('HF_API_KEY environment variable is required');
    }

    const client = new InferenceClient(HF_API_KEY);

    try {
        const result = await client.zeroShotClassification({
            inputs: text,
            model: 'facebook/bart-large-mnli',
            parameters: {
                candidate_labels: candidateTopics,
                multi_label: true,
            },
        });

        // result is an array of { label, score }
        return {
            text,
            topics: result.map(r => r.label),
            scores: result.map(r => r.score),
            topTopics: result.slice(0, 3).map(r => ({
                topic: r.label,
                confidence: r.score,
            })),
        };
    } catch (error) {
        console.error('Error in topic classification:', error);
        return {
            text,
            topics: ['general'],
            scores: [1.0],
            topTopics: [{ topic: 'general', confidence: 1.0 }],
        };
    }
}