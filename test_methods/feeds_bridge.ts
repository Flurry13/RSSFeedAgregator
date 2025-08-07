import { feeds } from '../feeds';

// Export feeds data for Python consumption
export function getFeedsData() {
    return feeds;
}

// Export feeds as JSON string
export function getFeedsJSON() {
    return JSON.stringify(feeds, null, 2);
}

// Export feeds with additional metadata
export function getFeedsWithMetadata() {
    return feeds.map(feed => ({
        ...feed,
        id: `${feed.group}_${feed.language}_${feeds.indexOf(feed)}`,
        needsTranslation: feed.language !== 'en'
    }));
}

// Get feeds by language
export function getFeedsByLanguage(language: string) {
    return feeds.filter(feed => feed.language === language);
}

// Get feeds by group
export function getFeedsByGroup(group: string) {
    return feeds.filter(feed => feed.group === group);
}

// Get all unique languages
export function getUniqueLanguages() {
    return [...new Set(feeds.map(feed => feed.language))];
}

// Get all unique groups
export function getUniqueGroups() {
    return [...new Set(feeds.map(feed => feed.group))];
}

// Main function to be called from Python
if (require.main === module) {
    console.log(JSON.stringify({
        feeds: feeds,
        languages: getUniqueLanguages(),
        groups: getUniqueGroups(),
        totalFeeds: feeds.length
    }));
} 