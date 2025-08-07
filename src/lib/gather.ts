
import { feeds } from '../feeds';
import { DOMParser } from '@xmldom/xmldom';
import { TranslationServiceClient } from '@google-cloud/translate';

const translateClient = new TranslationServiceClient()

const FEED_LIMIT = 999;
const HEADLINE_LIMIT = 999;

async function translate(text: string, targetLanguage: string) {
    const [translations] = await translateClient.translateText({
        parent: `projects/${process.env.GOOGLE_PROJECT_ID}`,
        contents: [text],
        targetLanguageCode: targetLanguage,
    });
    return translations.translations?.[0]?.translatedText || text;
}

export async function gather() {
    const headlines: Array<{title: string, source: string, pubDate: string}> = [];
    const amountBySource: Record<string, number> = {};
    const parser = new DOMParser();
    await Promise.all(
        feeds.slice(0, FEED_LIMIT).map(async (feed) => {
            try {
                const res = await fetch(feed.url);
                const xml = await res.text();
                const doc = parser.parseFromString(xml, "application/xml");
                const items = doc.getElementsByTagName("item");
                const feedHeadlines: Array<{title: string, source: string, pubDate: string}> = [];
                for (let i = 0; i < Math.min(items.length, HEADLINE_LIMIT); i++) {
                    const item = items[i];
                    const titleElement = item.getElementsByTagName("title")[0];
                    const srcElement = item.getElementsByTagName("link")[0];
                    const pubDateElement = item.getElementsByTagName("pubDate")[0];
                    if (titleElement && titleElement.textContent) {
                        const title = titleElement.textContent;
                        if (feed.language !== 'en') {
                            const headline = {
                                title: await translate(title, 'en'),
                                source: srcElement && srcElement.firstChild && srcElement.firstChild.nodeValue ? srcElement.firstChild.nodeValue : feed.url,
                                pubDate: pubDateElement && pubDateElement.textContent ? pubDateElement.textContent : "Date not available"
                            };
                            feedHeadlines.push(headline);
                        }
                        else {
                            const headline = {
                                title: title,
                                source: srcElement && srcElement.firstChild && srcElement.firstChild.nodeValue ? srcElement.firstChild.nodeValue : feed.url,
                                pubDate: pubDateElement && pubDateElement.textContent ? pubDateElement.textContent : "Date not available"
                            };
                            feedHeadlines.push(headline);
                        }
                    }
                }
                headlines.push(...feedHeadlines);
                amountBySource[feed.url] = feedHeadlines.length;
            } catch (error) {
                console.error(`Error fetching ${feed.url}:`, error);
            }
        })
    );
    return { headlines, amountBySource };
}