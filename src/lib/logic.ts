"use server"

import { NextRequest, NextResponse } from "next/server";
import OpenAI from 'openai';
import { feeds } from '../feeds';
import { DOMParser } from '@xmldom/xmldom';
import { classify } from "./classify";


export async function getFeeds() {
    return feeds
}

const FEED_LIMIT  = 999;
const HEADLINE_LIMIT = 999;

export async function GET(req: NextRequest) {
    let headlines: Array<{title: string, source: string}> = [];
    let amountBySource: Array<{source: string, amount: number}> = [];
    const parser = new DOMParser();
    await Promise.all(
        feeds.slice(0, FEED_LIMIT).map(async (feed) => {
            try {
                const res = await fetch(feed.url);
                const xml = await res.text();
                const doc = parser.parseFromString(xml, "application/xml");
                
                // Use xmldom's getElementsByTagName instead of querySelectorAll
                const items = doc.getElementsByTagName("item");
                const feedHeadlines: Array<{title: string, source: string, pubDate: string}> = [];
                
                for (let i = 0; i < Math.min(items.length, HEADLINE_LIMIT); i++) {
                    const item = items[i];
                    const titleElement = item.getElementsByTagName("title")[0];
                    const srcElement = item.getElementsByTagName("link")[0]; // Changed from "src" to "source"
                    const pubDateElement = item.getElementsByTagName("pubDate")[0];
                    if (titleElement && titleElement.textContent) {
                        const headline = {
                            title: titleElement.textContent,
                            source: srcElement && srcElement.firstChild && srcElement.firstChild.nodeValue ? srcElement.firstChild.nodeValue : feed.url, // Use feed URL as fallback
                            pubDate: pubDateElement && pubDateElement.textContent ? pubDateElement.textContent : "Date not available"
                        };
                        feedHeadlines.push(headline);
                    }

                }
                
                headlines.push(...feedHeadlines);
                amountBySource.push({source: feed.url, amount: feedHeadlines.length});
            } catch (e) {
                console.error(`Failed to fetch ${feed.url}:`, e);
                return;
            }
        })
    );

    const titles = headlines.map(h => h.title);
    const BATCH_SIZE = 5;
    let classifiedHeadlines: any[] = [];
    
    console.log(`\n=== STARTING OPENAI CLASSIFICATION ===`);
    console.log(`Total headlines to classify: ${titles.length}`);
    console.log(`Batch size: ${BATCH_SIZE}`);
    console.log(`Total batches: ${Math.ceil(titles.length / BATCH_SIZE)}`);
    
    // for (let i = 0; i < titles.length; i += BATCH_SIZE) {
    //     const batch = titles.slice(i, i + BATCH_SIZE);
    //     const batchNumber = Math.floor(i / BATCH_SIZE) + 1;
    //     const totalBatches = Math.ceil(titles.length / BATCH_SIZE);
        
    //     console.log(`Processing batch ${batchNumber}/${totalBatches} (${batch.length} headlines)...`);
        
    //     try {
    //         const result = await classifyHeadlines(batch);
    //         classifiedHeadlines = classifiedHeadlines.concat(result);
    //         console.log(`✅ Batch ${batchNumber} completed successfully`);
    //     } catch (error) {
    //         console.error(`❌ Batch ${batchNumber} failed:`, error);
    //         // Add empty classifications for failed batch to maintain array alignment
    //         const emptyClassifications = batch.map(() => ({
    //             original_headline: '',
    //             translated_headline: '',
    //             normalized_topic: 'Other',
    //             generalized_event: 'Unknown',
    //             region: 'Unknown',
    //             main_entity: 'Unknown'
    //         }));
    //         classifiedHeadlines = classifiedHeadlines.concat(emptyClassifications);
    //     }
    // }
    
    // console.log(`🎉 OpenAI classification completed! Classified ${classifiedHeadlines.length} headlines`);
    
    for (let i = 0; i < headlines.length; i++) {
        headlines[i] = { ...headlines[i], ...classifiedHeadlines[i]};
    }

    return NextResponse.json({ headlines, amountBySource });
}
