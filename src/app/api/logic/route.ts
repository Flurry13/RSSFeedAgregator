import { NextResponse } from 'next/server';
import { gather } from '../../../lib/gather';
import { classifyBatch } from '../../../lib/classify';

export async function GET() {
  try {
    console.log('🚀 Starting RSS feed processing...');
    
    // Gather headlines from RSS feeds
    const { headlines, amountBySource } = await gather();
    console.log(`📰 Gathered ${headlines.length} headlines from RSS feeds`);
    
    // Limit to 12 headlines to test rate limiting (4 groups of 3)
    const limitedHeadlines = headlines.slice(0, 12);
    console.log(`🧪 Testing with ${limitedHeadlines.length} headlines (4 groups of 3)`);
    
    // Extract just the titles for batch classification
    const titles = limitedHeadlines.map(headline => headline.title);
    console.log(`📝 Extracted ${titles.length} titles for classification`);
    
    // Classify all headlines in batches
    console.log('🔍 Starting batch classification...');
    const startTime = Date.now();
    const classifications = await classifyBatch(titles);
    const endTime = Date.now();
    console.log(`✅ Batch classification completed in ${endTime - startTime}ms`);
    
    // Combine headlines with their classifications
    const classifiedHeadlines = limitedHeadlines.map((headline, index) => ({
      ...headline,
      classification: classifications[index]
    }));

    console.log(`🎉 Successfully processed ${classifiedHeadlines.length} headlines`);

    return NextResponse.json({
      headlines: classifiedHeadlines,
      amountBySource,
      total: classifiedHeadlines.length,
      originalTotal: headlines.length,
      processingTime: endTime - startTime
    });

  } catch (error) {
    console.error('❌ Error in API route:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
} 