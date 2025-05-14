#!/usr/bin/env python3
# scripts/hourly_update.py
import os
import subprocess
import time
import json
import datetime
import sys
import argparse
from pathlib import Path

# Import your scrapers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.tiktok_scraper import TikTokTrendScraper

class TrendAnalyzer:
    def __init__(self):
        self.data_dir = Path("data")
        self.charts_dir = Path("charts")
        self.docs_dir = Path("docs")
        self.last_run_file = self.data_dir / "last_run_data.json"
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories"""
        for directory in [self.data_dir, self.charts_dir, self.docs_dir]:
            directory.mkdir(exist_ok=True)
    
    def run_pipeline(self):
   
        print(f"[{datetime.datetime.now()}] Starting hourly trend update...")
    
    # 1. Run unified scraper
        result = self.run_scraper()
    
        if not result:
            print("Scraping failed. Aborting update.")
            return False
    
    # 2. The data is already combined in the result, so we can skip that step
        combined_data = result
    
    # 3. Check if trends have changed significantly
        if not self.have_trends_changed(combined_data):
            print("No significant trend changes detected. Skipping analysis.")
            return False
        
    # 4. Run trend analysis
        analyzed_data = self.analyze_trends(combined_data)
    
    # 5. Save dashboard data
        self.save_dashboard_data(analyzed_data)
    
    # 6. Push changes to GitHub
        self.push_to_github()
    
        print(f"[{datetime.datetime.now()}] Hourly update completed successfully!")
        return True
    
    def run_continuously(self, interval=3600):
        """Run the pipeline continuously with specified interval in seconds"""
        print(f"Starting automatic updates every {interval} seconds")
        
        try:
            while True:
                # Run the pipeline
                success = self.run_pipeline()
                
                # Log result
                if success:
                    print(f"[{datetime.datetime.now()}] Update completed successfully!")
                else:
                    print(f"[{datetime.datetime.now()}] Update failed or no changes detected")
                    
                # Run AI analysis if available
                try:
                    from scripts.ai_analyzer import AITrendAnalyzer
                    ai_analyzer = AITrendAnalyzer()
                    ai_analyzer.analyze()
                    print(f"[{datetime.datetime.now()}] AI analysis completed")
                except ImportError:
                    print("AI analyzer not available, skipping AI analysis")
                except Exception as e:
                    print(f"Error in AI analysis: {e}")
                
                # Calculate and show next update time
                next_update = datetime.datetime.now() + datetime.timedelta(seconds=interval)
                print(f"Next update scheduled for: {next_update}")
                
                # Sleep until next update
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("Updates stopped by user")
        except Exception as e:
            print(f"Error in update loop: {e}")
            raise e
    
    def run_scraper(self):
   
         try:
             scraper = TikTokTrendScraper()
             return scraper.run_full_scrape()
         except Exception as e:
             print(f"Error running trend scraper: {e}")
             return None
    
    def combine_data(self, hashtag_data, song_data):
        """Combine data from both scrapers"""
        combined = {
            "hashtags_7d": hashtag_data.get("hashtags_7d", []),
            "hashtags_30d": hashtag_data.get("hashtags_30d", []),
            "trending_songs": song_data.get("trending_songs", []),
            "breakout_songs": song_data.get("breakout_songs", []),
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save raw combined data
        raw_data_path = self.data_dir / f"raw_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(raw_data_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
            
        # Save as current data
        current_data_path = self.data_dir / "current_data.json"
        with open(current_data_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
            
        return combined
    
    def have_trends_changed(self, current_data):
        """Check if trends have changed significantly since last run"""
        # If no previous run data, consider it changed
        if not self.last_run_file.exists():
            return True
            
        try:
            # Load last run data
            with open(self.last_run_file, "r", encoding="utf-8") as f:
                last_data = json.load(f)
                
            # Check if top 5 hashtags have changed
            last_top5 = set(h["hashtag"] for h in last_data.get("hashtags_7d", [])[:5])
            current_top5 = set(h["hashtag"] for h in current_data.get("hashtags_7d", [])[:5])
            
            hashtags_changed = len(last_top5.difference(current_top5)) >= 2  # At least 2 new hashtags
            
            # Check if top 3 songs have changed
            last_top3 = set(s["song_name"] for s in last_data.get("trending_songs", [])[:3])
            current_top3 = set(s["song_name"] for s in current_data.get("trending_songs", [])[:3])
            
            songs_changed = len(last_top3.difference(current_top3)) >= 1  # At least 1 new song
            
            # Save current as last run data
            with open(self.last_run_file, "w", encoding="utf-8") as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
                
            return hashtags_changed or songs_changed
            
        except Exception as e:
            print(f"Error checking trend changes: {e}")
            return True  # On error, assume changed
    
    def analyze_trends(self, data):
        """Perform trend analysis on the data"""
        # This is where you'd implement your trend analysis logic
        # For now, we'll just add some basic categorization and lifecycle stages
        
        # Process hashtags
        for hashtag_list in [data["hashtags_7d"], data["hashtags_30d"]]:
            for hashtag in hashtag_list:
                # Simple categorization based on text
                hashtag["categories"] = self.categorize_hashtag(hashtag["hashtag"])
                
                # Lifecycle stage based on ranking changes
                if hashtag.get("ranking_direction") == "up" and hashtag.get("ranking_change", 0) > 10:
                    hashtag["lifecycle_stage"] = "rising"
                elif hashtag.get("ranking_direction") == "up" and hashtag.get("ranking_change", 0) > 5:
                    hashtag["lifecycle_stage"] = "growing"
                elif hashtag.get("ranking_direction") == "down" and hashtag.get("ranking_change", 0) > 10:
                    hashtag["lifecycle_stage"] = "declining"
                else:
                    hashtag["lifecycle_stage"] = "stable"
        
        # Process songs
        for song_list in [data["trending_songs"], data["breakout_songs"]]:
            for song in song_list:
                song["categories"] = ["entertainment", "music"]
                
                # Breakout songs are always rising
                if song_list == data["breakout_songs"]:
                    song["lifecycle_stage"] = "rising"
                elif song.get("ranking_direction") == "up" and song.get("ranking_change", 0) > 5:
                    song["lifecycle_stage"] = "rising"
                elif song.get("ranking_direction") == "down" and song.get("ranking_change", 0) > 5:
                    song["lifecycle_stage"] = "declining"
                else:
                    song["lifecycle_stage"] = "stable"
        
        # Create hashtag clusters (simple text similarity)
        data["hashtag_clusters"] = self.cluster_hashtags(data["hashtags_7d"])
        
        # Identify emerging trends
        data["emerging_trends"] = self.identify_emerging_trends(data)
        
        # Category analysis
        data["category_analysis"] = self.analyze_categories(data["hashtags_7d"])
        
        return data
    
    def categorize_hashtag(self, hashtag_text):
        """Simple categorization of hashtags"""
        text = hashtag_text.lower().replace("#", "").replace("_", " ").replace("-", " ")
        
        categories = []
        
        # Define category keywords
        category_keywords = {
            "entertainment": ["dance", "challenge", "meme", "funny", "comedy", "viral", "trend"],
            "lifestyle": ["fashion", "beauty", "outfit", "style", "aesthetic"],
            "food": ["food", "recipe", "cooking", "meal", "baking", "chef"],
            "family": ["mother", "mom", "family", "dad", "father", "kid", "parent", "child"],
            "travel": ["travel", "vacation", "trip", "destination", "journey"],
            "fitness": ["workout", "fitness", "gym", "exercise", "health"]
        }
        
        # Check for each category
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    categories.append(category)
                    break
        
        if not categories:
            categories = ["other"]
            
        return categories
    
    def cluster_hashtags(self, hashtags):
        """Simple clustering of hashtags based on text similarity"""
        clusters = []
        processed = set()
        
        for i, hashtag1 in enumerate(hashtags):
            if hashtag1["hashtag"] in processed:
                continue
                
            cluster_items = [hashtag1]
            processed.add(hashtag1["hashtag"])
            
            # Find similar hashtags
            for hashtag2 in hashtags[i+1:]:
                if self.are_hashtags_similar(hashtag1, hashtag2):
                    cluster_items.append(hashtag2)
                    processed.add(hashtag2["hashtag"])
            
            # Only create clusters with at least 2 items
            if len(cluster_items) >= 2:
                # Get common categories
                all_categories = []
                for item in cluster_items:
                    all_categories.extend(item.get("categories", []))
                
                # Count categories and get top ones
                category_counts = {}
                for category in all_categories:
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                top_categories = sorted(category_counts.keys(), 
                                       key=lambda x: category_counts[x], 
                                       reverse=True)[:2]
                
                # Create cluster object
                cluster = {
                    "id": f"cluster_{len(clusters)}",
                    "items": [{"hashtag": item["hashtag"], "rank": item["rank"]} 
                              for item in cluster_items],
                    "size": len(cluster_items),
                    "categories": top_categories,
                    "trend_strength": sum(1 for item in cluster_items 
                                         if item.get("lifecycle_stage") in ["rising", "growing"])
                }
                
                clusters.append(cluster)
        
        return clusters
    
    def are_hashtags_similar(self, hashtag1, hashtag2):
        """Check if two hashtags are similar based on text"""
        text1 = hashtag1["hashtag"].lower().replace("#", "")
        text2 = hashtag2["hashtag"].lower().replace("#", "")
        
        # Check for substring
        if text1 in text2 or text2 in text1:
            return True
            
        # Check for common words
        words1 = set(text1.split())
        words2 = set(text2.split())
        common_words = words1.intersection(words2)
        
        if common_words and len(common_words) / max(len(words1), len(words2)) > 0.5:
            return True
            
        return False
    
    def identify_emerging_trends(self, data):
        """Identify emerging trends"""
        emerging = []
        
        # Check hashtags with high growth/momentum
        for hashtag in data["hashtags_7d"]:
            if (hashtag.get("ranking_direction") == "up" and hashtag.get("ranking_change", 0) > 8) or \
               (hashtag.get("period_momentum") == "accelerating"):
                emerging.append({
                    "type": "hashtag",
                    "item": hashtag["hashtag"],
                    "confidence": min(95, 50 + hashtag.get("ranking_change", 0) * 3),
                    "categories": hashtag.get("categories", ["other"]),
                    "post_count": hashtag.get("post_count", "N/A")
                })
        
        # Add breakout songs
        for song in data["breakout_songs"]:
            emerging.append({
                "type": "song",
                "item": f"{song['song_name']} - {song.get('artist', 'Unknown')}",
                "confidence": 90,
                "categories": ["entertainment", "music"],
                "post_count": song.get("post_count", "N/A")
            })
            
        # Sort by confidence
        emerging.sort(key=lambda x: x["confidence"], reverse=True)
        
        return emerging
    
    def analyze_categories(self, hashtags):
        """Analyze category distribution"""
        if not hashtags:
            return []
            
        # Count categories
        category_counts = {}
        for hashtag in hashtags:
            for category in hashtag.get("categories", ["other"]):
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate percentages
        total = sum(category_counts.values())
        category_analysis = []
        
        for category, count in category_counts.items():
            # Get top hashtags for this category
            category_hashtags = [h for h in hashtags if category in h.get("categories", [])]
            category_hashtags.sort(key=lambda x: x["rank"])
            
            top_hashtags = [{"hashtag": h["hashtag"], "rank": h["rank"]} 
                           for h in category_hashtags[:3]]
            
            category_analysis.append({
                "name": category,
                "count": count,
                "percentage": round((count / total) * 100, 1),
                "top_hashtags": top_hashtags
            })
        
        # Sort by count
        category_analysis.sort(key=lambda x: x["count"], reverse=True)
        
        return category_analysis
    
    def save_dashboard_data(self, data):
        """Save analyzed data for the dashboard"""
        dashboard_data_path = self.docs_dir / "trendData.json"
        with open(dashboard_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Dashboard data saved to {dashboard_data_path}")
    
    def push_to_github(self):
        """Push changes to GitHub"""
        try:
            print("Pushing changes to GitHub...")
            
            # Check git status to see what's changed
            status_output = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            
            if not status_output:
                print("No changes detected in git")
                return True
                
            # Add specific files only
            files_to_add = [
                "docs/trendData.json",
                "data/current_data.json",
                "data/last_run_data.json"
            ]
            
            # Add chart files if they exist
            chart_files = list(self.charts_dir.glob("*"))
            if chart_files:
                files_to_add.append("charts/*")
                
            # Add AI data if it exists
            ai_data_path = self.docs_dir / "aiTrendInsights.json"
            if ai_data_path.exists():
                files_to_add.append("docs/aiTrendInsights.json")
            
            # Only add files that exist
            for file_path in files_to_add:
                try:
                    subprocess.run(["git", "add", file_path], check=False)
                    print(f"Added {file_path} to git")
                except Exception as e:
                    print(f"Error adding {file_path}: {e}")
            
            # Check if we have any changes to commit
            status_after_add = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            if not status_after_add:
                print("No changes to commit after adding files")
                return True
            
            # Commit
            commit_message = f"Update trend data - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            
            # Push
            subprocess.run(["git", "push", "origin", "main"], check=True)
            
            print("Successfully pushed updates to GitHub")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error in git operations: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

# Run the pipeline if executed directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Trend Analyzer")
    parser.add_argument("--continuous", action="store_true", help="Run continuously with automatic updates")
    parser.add_argument("--interval", type=int, default=3600, help="Update interval in seconds (default: 3600 = 1 hour)")
    parser.add_argument("--force", action="store_true", help="Force update even if no significant changes detected")
    
    args = parser.parse_args()
    
    analyzer = TrendAnalyzer()
    
    if args.continuous:
        analyzer.run_continuously(interval=args.interval)
    else:
        analyzer.run_pipeline()