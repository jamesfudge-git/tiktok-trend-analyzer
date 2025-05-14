# scripts/ai_analyzer.py
import os
import json
import datetime
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download NLTK resources if needed
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class AITrendAnalyzer:
    def __init__(self):
        self.data_dir = Path("data")
        self.docs_dir = Path("docs")
        self.stop_words = set(stopwords.words('english'))
        self.additional_stopwords = {'tiktok', 'trend', 'video', 'challenge', 'viral', 
                                    'new', 'like', 'follow', 'share', 'hashtag', '#'}
        self.stop_words.update(self.additional_stopwords)
        
    def analyze(self, data=None):
        """Analyze trend data using AI techniques"""
        print(f"[{datetime.datetime.now()}] Starting AI trend analysis...")
        
        # Load data if not provided
        if data is None:
            try:
                current_data_path = self.data_dir / "current_data.json"
                with open(current_data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error loading trend data: {e}")
                return None
        
        # Run the analysis pipeline
        enhanced_data = data.copy()
        
        # 1. Topic modeling for hashtags
        enhanced_data["hashtag_topics"] = self.identify_hashtag_topics(
            enhanced_data.get("hashtags_7d", [])
        )
        
        # 2. Trend prediction scores
        enhanced_data["trend_predictions"] = self.predict_trend_future(
            enhanced_data.get("hashtags_7d", []),
            enhanced_data.get("hashtags_30d", [])
        )
        
        # 3. Content creation recommendations
        enhanced_data["content_recommendations"] = self.generate_content_recommendations(
            enhanced_data.get("hashtags_7d", []),
            enhanced_data.get("trending_songs", []),
            enhanced_data.get("hashtag_topics", [])
        )
        
        # Save enhanced AI data
        ai_data_path = self.docs_dir / "aiTrendInsights.json"
        with open(ai_data_path, "w", encoding="utf-8") as f:
            json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            
        # Update the main trend data with AI insights
        try:
            main_data_path = self.docs_dir / "trendData.json"
            with open(main_data_path, "r", encoding="utf-8") as f:
                main_data = json.load(f)
                
            # Add AI-enhanced data
            main_data["hashtag_topics"] = enhanced_data["hashtag_topics"]
            main_data["trend_predictions"] = enhanced_data["trend_predictions"]
            main_data["content_recommendations"] = enhanced_data["content_recommendations"]
            
            # Save updated main data
            with open(main_data_path, "w", encoding="utf-8") as f:
                json.dump(main_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error updating main trend data with AI insights: {e}")
        
        print(f"[{datetime.datetime.now()}] AI trend analysis completed!")
        return enhanced_data
    
    def identify_hashtag_topics(self, hashtags, num_topics=5):
        """Use LDA topic modeling to identify latent topics in hashtags"""
        print("Identifying hashtag topics...")
        
        if not hashtags:
            return []
            
        # Prepare corpus from hashtag texts
        corpus = []
        for hashtag in hashtags:
            # Clean the hashtag text
            text = hashtag["hashtag"].lower().replace("#", "").replace("_", " ").replace("-", " ")
            corpus.append(text)
        
        if len(corpus) < 5:  # Need enough data for meaningful topics
            return self._generate_default_topics()
            
        try:
            # Create document-term matrix
            vectorizer = CountVectorizer(
                stop_words=self.stop_words,
                min_df=2,  # Ignore terms that appear in less than 2 documents
                max_df=0.9  # Ignore terms that appear in more than 90% of documents
            )
            
            # If we have very few hashtags, adjust the min_df
            if len(corpus) < 10:
                vectorizer = CountVectorizer(
                    stop_words=self.stop_words,
                    min_df=1,
                    max_df=0.95
                )
                
            dtm = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            
            # If the DTM is empty, return default topics
            if dtm.sum() == 0:
                return self._generate_default_topics()
            
            # Apply LDA
            lda = LatentDirichletAllocation(
                n_components=min(num_topics, len(corpus) // 2 + 1),
                random_state=42
            )
            lda.fit(dtm)
            
            # Extract topics
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                # Get top words for this topic
                top_word_indices = topic.argsort()[:-11:-1]  # Get indices of top 10 words
                top_words = [feature_names[i] for i in top_word_indices]
                
                # Generate topic name based on top words
                topic_name = self._generate_topic_name(top_words)
                
                # Find hashtags most associated with this topic
                topic_hashtags = []
                topic_scores = lda.transform(dtm)
                top_doc_indices = topic_scores[:, topic_idx].argsort()[::-1][:5]  # Top 5 hashtags
                
                for doc_idx in top_doc_indices:
                    if topic_scores[doc_idx, topic_idx] > 0.2:  # Only include if significant topic match
                        topic_hashtags.append({
                            "hashtag": hashtags[doc_idx]["hashtag"],
                            "rank": hashtags[doc_idx]["rank"],
                            "score": float(topic_scores[doc_idx, topic_idx])
                        })
                
                # Only add topic if it has associated hashtags
                if topic_hashtags:
                    topics.append({
                        "id": f"topic_{topic_idx + 1}",
                        "name": topic_name,
                        "keywords": top_words[:5],
                        "hashtags": topic_hashtags,
                        "strength": float(np.mean([h["score"] for h in topic_hashtags]))
                    })
            
            # Sort topics by strength
            topics.sort(key=lambda x: x["strength"], reverse=True)
            
            # If we couldn't identify any topics, return defaults
            if not topics:
                return self._generate_default_topics()
                
            return topics
            
        except Exception as e:
            print(f"Error in topic modeling: {e}")
            return self._generate_default_topics()
    
    def _generate_topic_name(self, top_words):
        """Generate a descriptive name for a topic based on top words"""
        # Map common words to topic categories
        topic_categories = {
            "dance": ["dance", "dancing", "choreography", "moves", "routine"],
            "fashion": ["outfit", "fashion", "style", "clothes", "wearing", "aesthetic"],
            "food": ["food", "recipe", "cooking", "baking", "meal", "delicious", "eat"],
            "comedy": ["funny", "comedy", "joke", "humor", "laugh", "meme"],
            "beauty": ["makeup", "skincare", "beauty", "tutorial", "routine"],
            "fitness": ["workout", "fitness", "gym", "exercise", "training"],
            "lifestyle": ["morning", "routine", "life", "day", "productive"],
            "travel": ["travel", "trip", "adventure", "vacation", "destination"],
            "education": ["learn", "facts", "educational", "lesson", "teaching"],
            "gaming": ["game", "gaming", "player", "play", "level"],
            "music": ["song", "music", "sound", "audio", "beat", "remix"]
        }
        
        # Check if any top words match our categories
        for category, keywords in topic_categories.items():
            if any(word in keywords for word in top_words[:3]):
                return f"{category.capitalize()} Content"
        
        # If no clear match, use the most frequent word
        if top_words:
            main_word = top_words[0].capitalize()
            return f"{main_word}-Based Content"
        
        return "Misc Content"
    
    def _generate_default_topics(self):
        """Generate default topics when analysis fails"""
        return [
            {
                "id": "topic_1",
                "name": "Entertainment Content",
                "keywords": ["dance", "challenge", "funny", "comedy", "trend"],
                "hashtags": [],
                "strength": 0.85
            },
            {
                "id": "topic_2",
                "name": "Lifestyle Content",
                "keywords": ["lifestyle", "routine", "daily", "tips", "hacks"],
                "hashtags": [],
                "strength": 0.75
            },
            {
                "id": "topic_3",
                "name": "Food Content",
                "keywords": ["food", "recipe", "cooking", "meal", "delicious"],
                "hashtags": [],
                "strength": 0.7
            }
        ]
    
    def predict_trend_future(self, hashtags_7d, hashtags_30d):
        """Predict future performance of trends"""
        print("Predicting trend futures...")
        
        predictions = []
        
        # Create a map of 30-day hashtags for quick lookup
        hashtags_30d_map = {h["hashtag"]: h for h in hashtags_30d} if hashtags_30d else {}
        
        for hashtag in hashtags_7d:
            # Basic data
            prediction = {
                "hashtag": hashtag["hashtag"],
                "current_rank": hashtag["rank"],
                "current_stage": hashtag.get("lifecycle_stage", "stable")
            }
            
            # Calculate prediction score (higher = more likely to grow)
            score = 50  # Base score
            
            # Factor 1: Current ranking direction and magnitude
            if hashtag.get("ranking_direction") == "up":
                score += min(hashtag.get("ranking_change", 0) * 2, 20)
            elif hashtag.get("ranking_direction") == "down":
                score -= min(hashtag.get("ranking_change", 0) * 2, 20)
            
            # Factor 2: Current lifecycle stage
            if hashtag.get("lifecycle_stage") == "rising":
                score += 15
            elif hashtag.get("lifecycle_stage") == "growing":
                score += 10
            elif hashtag.get("lifecycle_stage") == "declining":
                score -= 15
            
            # Factor 3: Momentum compared to 30-day data
            if hashtag["hashtag"] in hashtags_30d_map:
                h30 = hashtags_30d_map[hashtag["hashtag"]]
                
                # Compare rankings
                if hashtag["rank"] < h30["rank"]:  # Improved in rank
                    score += 10
                elif hashtag["rank"] > h30["rank"]:  # Declined in rank
                    score -= 5
                
                # Check period momentum if available
                if hashtag.get("period_momentum") == "accelerating":
                    score += 15
                elif hashtag.get("period_momentum") == "decelerating":
                    score -= 10
            else:
                # New hashtag (not in 30-day data)
                score += 5  # Slight bonus for being new
            
            # Factor 4: Post count and engagement
            post_count = hashtag.get("numeric_post_count", 0)
            if post_count > 1000000:  # Over 1M posts
                score += 5
            elif post_count > 100000:  # Over 100K posts
                score += 3
            
            # Determine prediction status
            prediction_status = "stable"
            if score >= 70:
                prediction_status = "strongly_rising"
            elif score >= 60:
                prediction_status = "rising"
            elif score <= 30:
                prediction_status = "strongly_declining"
            elif score <= 40:
                prediction_status = "declining"
            
            # Add to prediction
            prediction["score"] = min(max(score, 5), 95)  # Cap between 5-95
            prediction["status"] = prediction_status
            prediction["longevity"] = self._estimate_trend_longevity(prediction_status)
            
            predictions.append(prediction)
        
        # Sort predictions by score (descending)
        predictions.sort(key=lambda x: x["score"], reverse=True)
        
        return predictions
    
    def _estimate_trend_longevity(self, status):
        """Estimate how long a trend will remain relevant based on status"""
        if status == "strongly_rising":
            return "2-3 weeks"
        elif status == "rising":
            return "1-2 weeks"
        elif status == "stable":
            return "5-7 days"
        elif status == "declining":
            return "2-4 days"
        else:  # strongly_declining
            return "1-2 days"
    
    def generate_content_recommendations(self, hashtags, songs, topics=None):
        """Generate AI-powered content creation recommendations"""
        print("Generating content recommendations...")
        
        # Start with basic recommendations
        recommendations = {
            "top_combinations": [],
            "content_strategies": [],
            "audience_insights": self._generate_audience_insights()
        }
        
        # Generate hashtag-song combinations
        if hashtags and songs:
            top_hashtags = hashtags[:min(5, len(hashtags))]
            top_songs = songs[:min(3, len(songs))]
            
            combinations = []
            for i, hashtag in enumerate(top_hashtags):
                song = top_songs[i % len(top_songs)]
                
                combo = {
                    "hashtag": hashtag["hashtag"],
                    "song": f"{song['song_name']} - {song.get('artist', 'Unknown')}",
                    "fit_score": self._calculate_combination_score(hashtag, song)
                }
                
                combinations.append(combo)
            
            # Sort by fit score
            combinations.sort(key=lambda x: x["fit_score"], reverse=True)
            recommendations["top_combinations"] = combinations[:3]
        
        # Generate content strategies based on topics
        if topics:
            for topic in topics[:min(3, len(topics))]:
                strategy = {
                    "topic": topic["name"],
                    "hashtags": [h["hashtag"] for h in topic["hashtags"][:3]],
                    "approach": self._generate_content_approach(topic["name"], topic["keywords"])
                }
                recommendations["content_strategies"].append(strategy)
        else:
            # Default strategies if no topics
            default_strategies = [
                {
                    "topic": "Entertainment Content",
                    "hashtags": [h["hashtag"] for h in hashtags[:3]] if hashtags else [],
                    "approach": "Create short, engaging videos featuring trending sounds with a comedic twist."
                },
                {
                    "topic": "Tutorial Content",
                    "hashtags": [h["hashtag"] for h in hashtags[3:6]] if len(hashtags) > 3 else [],
                    "approach": "Share quick, helpful tutorials that solve common problems or teach useful skills."
                }
            ]
            recommendations["content_strategies"] = default_strategies
        
        return recommendations
    
    def _calculate_combination_score(self, hashtag, song):
        """Calculate how well a hashtag and song fit together"""
        # This would ideally use NLP/ML to determine compatibility
        # For now, use a simpler heuristic
        base_score = 70  # Start with a reasonable score
        
        # Boost score if both are trending upward
        if hashtag.get("ranking_direction") == "up" and song.get("ranking_direction") == "up":
            base_score += 15
        
        # Boost score if both are in "rising" stage
        if hashtag.get("lifecycle_stage") == "rising" and song.get("lifecycle_stage") == "rising":
            base_score += 10
        
        # Randomize slightly for variety
        base_score += np.random.randint(-5, 6)
        
        # Cap the score between 60 and 95
        return min(max(base_score, 60), 95)
    
    def _generate_content_approach(self, topic_name, keywords):
        """Generate a content approach based on topic and keywords"""
        topic_lower = topic_name.lower()
        
        if "dance" in topic_lower or "choreography" in topic_lower:
            return "Create short dance videos featuring simple choreography that's easy for viewers to learn and recreate."
            
        elif "comedy" in topic_lower or "funny" in topic_lower:
            return "Develop humorous skits or situational comedy that's relatable to your audience. Focus on unexpected twists and authenticity."
            
        elif "food" in topic_lower or "recipe" in topic_lower:
            return "Share quick recipe tutorials with visually appealing results. Focus on easy-to-make items with common ingredients."
            
        elif "fashion" in topic_lower or "outfit" in topic_lower:
            return "Create outfit inspiration videos with styling tips. Focus on trend combinations and accessible fashion choices."
            
        elif "beauty" in topic_lower or "makeup" in topic_lower:
            return "Film quick beauty tutorials focusing on specific techniques. Before-and-after transformations perform particularly well."
            
        elif "lifestyle" in topic_lower:
            return "Share authentic day-in-the-life content or productivity hacks that resonate with your target audience."
            
        elif "fitness" in topic_lower or "workout" in topic_lower:
            return "Demonstrate effective exercise routines that can be done in small spaces with minimal equipment."
            
        else:
            # Generic approach based on keywords
            if keywords and len(keywords) >= 2:
                return f"Create content focusing on {keywords[0]} and {keywords[1]}, with an emphasis on authentic, personal experiences that viewers can relate to."
            else:
                return "Focus on creating authentic, personality-driven content that aligns with current trends while staying true to your unique voice."
    
    def _generate_audience_insights(self):
        """Generate audience insights for different content categories"""
        return [
            {
                "category": "Entertainment",
                "primary_demographic": "Gen Z (16-24)",
                "peak_engagement_times": ["7-9 PM", "9-11 PM"],
                "retention_drivers": "Humor, relatability, and trend participation"
            },
            {
                "category": "Lifestyle",
                "primary_demographic": "Millennials (25-34)",
                "peak_engagement_times": ["6-8 AM", "8-10 PM"],
                "retention_drivers": "Authenticity, aesthetics, and practical tips"
            },
            {
                "category": "Education",
                "primary_demographic": "Mixed (18-45)",
                "peak_engagement_times": ["12-2 PM", "7-9 PM"],
                "retention_drivers": "Concise information, visual demonstrations, and unique facts"
            }
        ]

# Run the analyzer if executed directly
if __name__ == "__main__":
    analyzer = AITrendAnalyzer()
    analyzer.analyze()