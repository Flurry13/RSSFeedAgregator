import { gather } from './gather';
import { eventGroupingService, type EventGroup } from './eventGrouping';

/**
 * Example: Group RSS headlines by events
 */
export async function groupRSSHeadlinesByEvents() {
    try {
        console.log('Gathering RSS headlines...');
        
        // Gather headlines from RSS feeds
        const { headlines } = await gather();
        
        console.log(`Found ${headlines.length} headlines`);
        
        // Convert to the format expected by the event grouping service
        const formattedHeadlines = headlines.map(headline => ({
            title: headline.title,
            source: headline.source,
            pubDate: headline.pubDate,
            topics: [], // Will be filled by the service
            scores: []
        }));
        
        console.log('Grouping headlines by events...');
        
        // Group headlines by events
        const result = await eventGroupingService.groupHeadlinesByEvents(
            formattedHeadlines,
            0.7, // similarity threshold
            2    // minimum cluster size
        );
        
        console.log(`\nEvent Grouping Results:`);
        console.log(`- Total groups: ${result.total_groups}`);
        console.log(`- Grouped headlines: ${result.total_grouped}`);
        console.log(`- Ungrouped headlines: ${result.total_ungrouped}`);
        
        // Display event groups
        result.event_groups.forEach((group, index) => {
            console.log(`\nEvent ${index + 1}: ${group.event_name}`);
            console.log(`  Type: ${group.event_type}`);
            console.log(`  Similarity: ${group.similarity_score.toFixed(3)}`);
            console.log(`  Headlines: ${group.headlines.length}`);
            console.log(`  Keywords: ${group.event_keywords.join(', ')}`);
            console.log(`  Entities: ${group.top_entities.join(', ')}`);
            console.log(`  Locations: ${group.locations.join(', ')}`);
            
            group.headlines.forEach((headline, i) => {
                console.log(`    ${i + 1}. ${headline.title} (${headline.source})`);
            });
        });
        
        // Analyze the results
        const analysis = eventGroupingService.analyzeEventGroups(result.event_groups);
        console.log(`\nAnalysis:`);
        console.log(`- Average similarity: ${analysis.averageSimilarity.toFixed(3)}`);
        console.log(`- Event type distribution:`, analysis.eventTypeDistribution);
        console.log(`- Total unique keywords: ${analysis.eventKeywords.length}`);
        
        if (analysis.largestEvent) {
            console.log(`- Largest event: "${analysis.largestEvent.event_name}" with ${analysis.largestEvent.headlines.length} headlines`);
        }
        
        return result;
        
    } catch (error) {
        console.error('Error grouping headlines by events:', error);
        throw error;
    }
}

/**
 * Example: Filter and sort event groups
 */
export function filterAndSortEventGroups(eventGroups: EventGroup[]) {
    // Filter by event type
    const politicalEvents = eventGroupingService.filterEventGroups(eventGroups, {
        eventType: 'politics'
    });
    
    console.log(`Found ${politicalEvents.length} political events`);
    
    // Filter by similarity threshold
    const highSimilarityEvents = eventGroupingService.filterEventGroups(eventGroups, {
        minSimilarity: 0.8
    });
    
    console.log(`Found ${highSimilarityEvents.length} high-similarity events`);
    
    // Sort by number of headlines (descending)
    const sortedByHeadlines = eventGroupingService.sortEventGroups(
        eventGroups,
        'headlines',
        'desc'
    );
    
    console.log('Top 3 events by headline count:');
    sortedByHeadlines.slice(0, 3).forEach((group, index) => {
        console.log(`${index + 1}. ${group.event_name} (${group.headlines.length} headlines)`);
    });
    
    return {
        politicalEvents,
        highSimilarityEvents,
        sortedByHeadlines
    };
}

/**
 * Example: Real-time event monitoring
 */
export async function monitorEventsInRealTime() {
    console.log('Starting real-time event monitoring...');
    
    // Check if backend is healthy
    const isHealthy = await eventGroupingService.healthCheck();
    if (!isHealthy) {
        console.error('Backend is not healthy. Please start the Python server.');
        return;
    }
    
    console.log('Backend is healthy. Starting monitoring...');
    
    // This would typically run in a loop or be triggered by new RSS feeds
    setInterval(async () => {
        try {
            const { headlines } = await gather();
            
            if (headlines.length > 0) {
                const formattedHeadlines = headlines.map(headline => ({
                    title: headline.title,
                    source: headline.source,
                    pubDate: headline.pubDate,
                    topics: [],
                    scores: []
                }));
                
                const result = await eventGroupingService.groupHeadlinesByEvents(
                    formattedHeadlines,
                    0.7,
                    2
                );
                
                if (result.total_groups > 0) {
                    console.log(`\n[${new Date().toISOString()}] New events detected:`);
                    result.event_groups.forEach(group => {
                        console.log(`  - ${group.event_name} (${group.headlines.length} headlines)`);
                    });
                }
            }
        } catch (error) {
            console.error('Error in real-time monitoring:', error);
        }
    }, 300000); // Check every 5 minutes
}

/**
 * Example: Integration with existing classification system
 */
export async function integrateWithExistingClassification() {
    try {
        // Gather headlines
        const { headlines } = await gather();
        
        // Use existing classification first
        const classifiedHeadlines = await Promise.all(
            headlines.map(async (headline) => {
                // This would use your existing classify function
                // For now, we'll just use the basic structure
                return {
                    title: headline.title,
                    source: headline.source,
                    pubDate: headline.pubDate,
                    topics: ['general'], // Placeholder
                    scores: [1.0]
                };
            })
        );
        
        // Then group by events
        const result = await eventGroupingService.groupHeadlinesByEvents(
            classifiedHeadlines,
            0.7,
            2
        );
        
        console.log('Integration complete!');
        console.log(`- Original headlines: ${headlines.length}`);
        console.log(`- Event groups: ${result.total_groups}`);
        console.log(`- Grouped headlines: ${result.total_grouped}`);
        
        return result;
        
    } catch (error) {
        console.error('Error in integration:', error);
        throw error;
    }
}

// Example usage - uncomment to run
/*
groupRSSHeadlinesByEvents()
    .then(() => console.log('Example completed successfully'))
    .catch(error => console.error('Example failed:', error));
*/ 