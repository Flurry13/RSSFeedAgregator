import { classify } from './classify';

export interface Headline {
    title: string;
    source: string;
    pubDate: string;
    topics?: string[];
    scores?: number[];
}

export interface EventGroup {
    event_id: string;
    event_name: string;
    headlines: Headline[];
    similarity_score: number;
    event_keywords: string[];
    event_type: string;
    top_entities: string[];
    locations: string[];
    created_at: string;
}

export interface GroupingRequest {
    headlines: Headline[];
    similarity_threshold?: number;
    min_cluster_size?: number;
}

export interface GroupingResponse {
    event_groups: EventGroup[];
    ungrouped_headlines: Headline[];
    total_groups: number;
    total_grouped: number;
    total_ungrouped: number;
}

export class EventGroupingService {
    private baseUrl: string;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    /**
     * Group headlines by events using the Python backend
     */
    async groupHeadlinesByEvents(
        headlines: Headline[],
        similarityThreshold: number = 0.7,
        minClusterSize: number = 2
    ): Promise<GroupingResponse> {
        try {
            // First, classify headlines if they don't have topics
            const headlinesWithTopics = await this.ensureHeadlinesHaveTopics(headlines);

            const request: GroupingRequest = {
                headlines: headlinesWithTopics,
                similarity_threshold: similarityThreshold,
                min_cluster_size: minClusterSize
            };

            const response = await fetch(`${this.baseUrl}/group-headlines`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: GroupingResponse = await response.json();
            return result;
        } catch (error) {
            console.error('Error grouping headlines by events:', error);
            throw error;
        }
    }

    /**
     * Ensure headlines have topics by classifying them if needed
     */
    private async ensureHeadlinesHaveTopics(headlines: Headline[]): Promise<Headline[]> {
        const headlinesWithTopics = await Promise.all(
            headlines.map(async (headline) => {
                if (headline.topics && headline.topics.length > 0) {
                    return headline;
                }

                try {
                    const classification = await classify(headline.title);
                    return {
                        ...headline,
                        topics: classification.topics,
                        scores: classification.scores
                    };
                } catch (error) {
                    console.warn(`Failed to classify headline: ${headline.title}`, error);
                    return {
                        ...headline,
                        topics: ['general'],
                        scores: [1.0]
                    };
                }
            })
        );

        return headlinesWithTopics;
    }

    /**
     * Check if the backend is healthy
     */
    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }

    /**
     * Get model information from the backend
     */
    async getModelInfo(): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/model-info`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error getting model info:', error);
            throw error;
        }
    }

    /**
     * Analyze event groups and provide insights
     */
    analyzeEventGroups(eventGroups: EventGroup[]): {
        eventTypeDistribution: Record<string, number>;
        averageSimilarity: number;
        largestEvent: EventGroup | null;
        eventKeywords: string[];
    } {
        if (eventGroups.length === 0) {
            return {
                eventTypeDistribution: {},
                averageSimilarity: 0,
                largestEvent: null,
                eventKeywords: []
            };
        }

        // Event type distribution
        const eventTypeDistribution: Record<string, number> = {};
        eventGroups.forEach(group => {
            eventTypeDistribution[group.event_type] = (eventTypeDistribution[group.event_type] || 0) + 1;
        });

        // Average similarity
        const totalSimilarity = eventGroups.reduce((sum, group) => sum + group.similarity_score, 0);
        const averageSimilarity = totalSimilarity / eventGroups.length;

        // Largest event (most headlines)
        const largestEvent = eventGroups.reduce((largest, current) => 
            current.headlines.length > largest.headlines.length ? current : largest
        );

        // All event keywords
        const allKeywords = new Set<string>();
        eventGroups.forEach(group => {
            group.event_keywords.forEach(keyword => allKeywords.add(keyword));
        });

        return {
            eventTypeDistribution,
            averageSimilarity,
            largestEvent,
            eventKeywords: Array.from(allKeywords)
        };
    }

    /**
     * Filter event groups by various criteria
     */
    filterEventGroups(
        eventGroups: EventGroup[],
        filters: {
            eventType?: string;
            minSimilarity?: number;
            minHeadlines?: number;
            keywords?: string[];
        }
    ): EventGroup[] {
        return eventGroups.filter(group => {
            if (filters.eventType && group.event_type !== filters.eventType) {
                return false;
            }
            if (filters.minSimilarity && group.similarity_score < filters.minSimilarity) {
                return false;
            }
            if (filters.minHeadlines && group.headlines.length < filters.minHeadlines) {
                return false;
            }
            if (filters.keywords && filters.keywords.length > 0) {
                const hasKeyword = filters.keywords.some(keyword =>
                    group.event_keywords.some(k => k.toLowerCase().includes(keyword.toLowerCase()))
                );
                if (!hasKeyword) {
                    return false;
                }
            }
            return true;
        });
    }

    /**
     * Sort event groups by various criteria
     */
    sortEventGroups(
        eventGroups: EventGroup[],
        sortBy: 'similarity' | 'headlines' | 'created' | 'name' = 'similarity',
        order: 'asc' | 'desc' = 'desc'
    ): EventGroup[] {
        const sorted = [...eventGroups].sort((a, b) => {
            let comparison = 0;
            
            switch (sortBy) {
                case 'similarity':
                    comparison = a.similarity_score - b.similarity_score;
                    break;
                case 'headlines':
                    comparison = a.headlines.length - b.headlines.length;
                    break;
                case 'created':
                    comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                    break;
                case 'name':
                    comparison = a.event_name.localeCompare(b.event_name);
                    break;
            }
            
            return order === 'desc' ? -comparison : comparison;
        });

        return sorted;
    }
}

// Export a default instance
export const eventGroupingService = new EventGroupingService(); 