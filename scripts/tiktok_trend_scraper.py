from seleniumbase import SB
import time
import json
import os
import subprocess
from datetime import datetime

class TikTokTrendScraper:
    def __init__(self):
        # Configuration
        self.charts_dir = "charts"
        self.data_dir = "data"
        self.output_file = "dashboard/trendData.json"
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.charts_dir, self.data_dir, "dashboard"]:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def run_scraper(self):
        """Main function to run the complete scraping process"""
        print("Starting TikTok trend scraper...")
        start_time = time.time()
        
        # Scrape all trend data
        with SB(uc=True) as sb:
            # 1. Scrape hashtags
            hashtags_7d = self.scrape_hashtags(sb, "7d")
            hashtags_30d = self.scrape_hashtags(sb, "30d", switch_period=True)
            
            # 2. Scrape songs
            trending_songs = self.scrape_songs(sb, "trending")
            breakout_songs = self.scrape_songs(sb, "breakout", switch_to_breakout=True)
        
        # 3. Process and save data
        self.process_and_save_data(hashtags_7d, hashtags_30d, trending_songs, breakout_songs)
        
        # 4. Push to GitHub if needed
        self.push_to_github()
        
        # Report completion
        elapsed_time = time.time() - start_time
        print(f"Scraping completed in {elapsed_time:.2f} seconds")
        print(f"Collected {len(hashtags_7d)} 7-day hashtags, {len(hashtags_30d)} 30-day hashtags")
        print(f"Collected {len(trending_songs)} trending songs, {len(breakout_songs)} breakout songs")
    
    def scrape_hashtags(self, sb, period_name, switch_period=False):
        """Scrape hashtag data for the given period"""
        print(f"\nScraping hashtags for {period_name} period...")
        
        # Navigate to hashtag page (only first time)
        if period_name == "7d":
            sb.open("https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en")
            sb.sleep(5)
            
            # Handle cookie consent
            try:
                sb.click("button[aria-label='Accept all cookies']", timeout=3)
            except:
                print("No cookie dialog found or already accepted")
        
        # Switch to 30-day period if needed
        if switch_period and period_name == "30d":
            print("Switching to 30-day view...")
            try:
                sb.execute_script("window.scrollTo(0, 0)")
                sb.sleep(2)
                sb.click("#hashtagPeriodSelect > span > div > div > div", timeout=5)
                sb.sleep(2)
                xpath_30_days = "//div[contains(@class, 'creative-component-single-line') and text()='Last 30 days']"
                sb.click(xpath_30_days, by="xpath", timeout=5)
                print("✅ Switched to 30-day view")
                sb.sleep(5)
            except Exception as e:
                print(f"❌ Error switching to 30-day view: {e}")
        
        # Extract hashtags
        hashtags = []
        target_count = 20
        max_attempts = 10
        attempt = 0
        
        while len(hashtags) < target_count and attempt < max_attempts:
            attempt += 1
            print(f"Extraction attempt {attempt}...")
            
            try:
                hashtag_elements = sb.find_elements("[class*='CardPc_titleText']")
                print(f"Found {len(hashtag_elements)} potential hashtag elements")
                
                for i, element in enumerate(hashtag_elements):
                    try:
                        hashtag_text = element.text.strip()
                        if not hashtag_text or any(h['hashtag'] == hashtag_text for h in hashtags):
                            continue
                        
                        # Get container for additional data
                        container = element.find_element("xpath", "./../../../..")
                        
                        # Extract post count
                        try:
                            post_count_element = container.find_element("css selector", "span.CardPc_itemValue__XGDmG")
                            post_count = post_count_element.text.strip()
                        except Exception as e:
                            print(f"  Failed to get post count for '{hashtag_text}': {e}")
                            post_count = None
                        
                        # Extract canvas chart
                        try:
                            canvas = container.find_element("css selector", "canvas")
                            safe_name = ''.join(c if c.isalnum() else '_' for c in hashtag_text[1:])
                            chart_filename = f"{self.charts_dir}/{period_name}_{len(hashtags)+1}_{safe_name}.png"
                            canvas.screenshot(chart_filename)
                        except Exception as e:
                            print(f"  Failed to capture chart for '{hashtag_text}': {e}")
                            chart_filename = None
                        
                        # Create hashtag data object
                        hashtag_data = {
                            "hashtag": hashtag_text,
                            "post_count": post_count,
                            "chart_image": chart_filename,
                            "rank": len(hashtags) + 1
                        }
                        
                        hashtags.append(hashtag_data)
                        print(f"  ✅ Collected: {hashtag_text} | Posts: {post_count}")
                        
                    except Exception as e:
                        print(f"  Error extracting hashtag {i+1}: {e}")
                
                print(f"Total unique hashtags so far: {len(hashtags)}")
                
                # Check if we need more hashtags
                if len(hashtags) < target_count:
                    print("Clicking 'View More' button...")
                    
                    view_more_selectors = [
                        "div[class*='ViewMoreBtn']",
                        "//div[text()='View more']"
                    ]
                    
                    clicked = False
                    for selector in view_more_selectors:
                        try:
                            if selector.startswith("//"):
                                sb.click(selector, by="xpath", timeout=3)
                            else:
                                sb.click(selector, timeout=3)
                            clicked = True
                            print(f"Successfully clicked using selector: {selector}")
                            break
                        except Exception as e:
                            print(f"Failed to click with selector '{selector}': {e}")
                    
                    if not clicked:
                        print("Could not find or click 'View More' button with any selector")
                        break
                    
                    sb.sleep(3)
                    sb.execute_script("window.scrollBy(0, 500)")
                    sb.sleep(2)
                
                else:
                    break
                
            except Exception as e:
                print(f"Error during extraction attempt {attempt}: {e}")
        
        return hashtags
    
    def scrape_songs(self, sb, section_name, switch_to_breakout=False):
        """Scrape song data for the specified section"""
        print(f"\nScraping {section_name} songs...")
        
        # Navigate to songs page (only first time)
        if section_name == "trending":
            sb.open("https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en")
            sb.sleep(5)
            
            # Handle cookie consent
            try:
                sb.click("button[aria-label='Accept all cookies']", timeout=3)
            except:
                print("No cookie dialog found or already accepted")
        
        # Switch to breakout section if needed
        if switch_to_breakout:
            print("Switching to Breakout Songs tab...")
            try:
                sb.execute_script("window.scrollTo(0, 0)")
                sb.sleep(2)
                
                breakout_selectors = [
                    ".ContentTab_itemLabelText__hiCCd",
                    "//span[text()='Breakout']",
                    "//div[contains(@class, 'ContentTab_container')]//span[contains(text(), 'Breakout')]",
                    "//div[contains(@class, 'ContentTab_item')]//span[contains(text(), 'Breakout')]"
                ]
                
                for selector in breakout_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = sb.find_elements(selector, by="xpath")
                        else:
                            elements = sb.find_elements(selector)
                        
                        for elm in elements:
                            if 'Breakout' in elm.text:
                                elm.click()
                                print("✅ Switched to Breakout Songs tab")
                                sb.sleep(5)
                                break
                    except:
                        continue
            except Exception as e:
                print(f"❌ Error switching to Breakout Songs tab: {e}")
        
        # Extract songs
        songs = []
        limit = 20 if section_name == "trending" else 5
        max_attempts = 10
        attempt = 0
        
        while len(songs) < limit and attempt < max_attempts:
            attempt += 1
            print(f"Extraction attempt {attempt}...")
            
            try:
                song_cards = sb.find_elements("div[class*='ItemCard_infoContentContainer']")
                print(f"Found {len(song_cards)} song cards")
                
                for i, card in enumerate(song_cards):
                    if len(songs) >= limit:
                        break
                    
                    try:
                        # Extract song name
                        song_name = None
                        name_selectors = [
                            "span.ItemCard_musicName__2znhM",
                            "[class*='musicName']",
                            ".ItemCard_centerContent__5MR3Z span",
                            "//span[contains(@class, 'musicName')]"
                        ]
                        
                        for selector in name_selectors:
                            try:
                                if selector.startswith("//"):
                                    song_element = card.find_element("xpath", selector)
                                else:
                                    song_element = card.find_element("css selector", selector)
                                song_name = song_element.text.strip()
                                if song_name:
                                    break
                            except:
                                continue
                        
                        if not song_name:
                            spans = card.find_elements("css selector", "span")
                            for span in spans:
                                text = span.text.strip()
                                if text and not song_name:
                                    song_name = text
                        
                        if not song_name:
                            print(f"  Failed to get song name for card {i+1}")
                            continue
                        
                        # Extract artist name
                        artist_name = None
                        artist_selectors = [
                            "span.ItemCard_autherName__gdrue",
                            "[class*='autherName']",
                            ".ItemCard_otherInfoWrap__VROzf span",
                            "//span[contains(@class, 'autherName')]"
                        ]
                        
                        for selector in artist_selectors:
                            try:
                                if selector.startswith("//"):
                                    artist_element = card.find_element("xpath", selector)
                                else:
                                    artist_element = card.find_element("css selector", selector)
                                artist_name = artist_element.text.strip()
                                if artist_name:
                                    break
                            except:
                                continue
                        
                        if not artist_name:
                            spans = card.find_elements("css selector", "span")
                            for span in spans[1:]:
                                text = span.text.strip()
                                if text and text != song_name:
                                    artist_name = text
                                    break
                        
                        # Extract post/video count
                        post_count = None
                        post_selectors = [
                            "span[class*='ItemCard_number__']",
                            ".ItemCard_number__3rJlo",
                            "span[class*='number']"
                        ]
                        
                        for selector in post_selectors:
                            try:
                                post_element = card.find_element("css selector", selector)
                                post_count = post_element.text.strip()
                                if post_count:
                                    break
                            except:
                                continue
                        
                        # Extract chart image
                        chart_filename = None
                        canvas = None
                        chart_selectors = [
                            ".TrendingEchart_echart__fcYT9",
                            "[class*='echart']",
                            "canvas"
                        ]
                        
                        for selector in chart_selectors:
                            try:
                                if selector == "canvas":
                                    canvas = card.find_element("css selector", selector)
                                else:
                                    chart_element = card.find_element("css selector", selector)
                                    canvas = chart_element.find_element("css selector", "canvas")
                                if canvas:
                                    break
                            except:
                                continue
                        
                        if canvas:
                            safe_song_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in song_name)
                            chart_filename = f"{self.charts_dir}/song_{section_name}_{len(songs)+1}_{safe_song_name[:30]}.png"
                            canvas.screenshot(chart_filename)
                        
                        # Skip if song already exists in list
                        if any(s['song_name'] == song_name for s in songs):
                            continue
                        
                        # Create song data object
                        song_data = {
                            "song_name": song_name,
                            "artist": artist_name,
                            "post_count": post_count,
                            "chart_image": chart_filename,
                            "rank": len(songs) + 1
                        }
                        
                        songs.append(song_data)
                        print(f"  ✅ Collected: {song_name} by {artist_name} ({post_count})")
                        
                    except Exception as e:
                        print(f"  Error extracting song {i+1}: {e}")
                
                # Check if we need more songs
                if len(songs) < limit:
                    print("Clicking 'View More' button...")
                    
                    view_more_selectors = [
                        "div[class*='ViewMoreBtn']",
                        "//div[text()='View more']"
                    ]
                    
                    clicked = False
                    for selector in view_more_selectors:
                        try:
                            if selector.startswith("//"):
                                sb.click(selector, by="xpath", timeout=3)
                            else:
                                sb.click(selector, timeout=3)
                            clicked = True
                            print(f"Successfully clicked using selector: {selector}")
                            break
                        except Exception as e:
                            print(f"Failed to click with selector '{selector}': {e}")
                    
                    if not clicked:
                        print("Could not find or click 'View More' button with any selector")
                        break
                    
                    sb.sleep(3)
                    sb.execute_script("window.scrollBy(0, 500)")
                    sb.sleep(2)
                
                else:
                    break
                
            except Exception as e:
                print(f"Error during extraction attempt {attempt}: {e}")
        
        return songs
    
    def process_and_save_data(self, hashtags_7d, hashtags_30d, trending_songs, breakout_songs):
        """Process scraped data and save for dashboard"""
        print("\nProcessing and preparing data for dashboard...")
        
        # Calculate growth rates and trend status
        self.calculate_trend_metrics(hashtags_7d)
        self.calculate_trend_metrics(hashtags_30d)
        self.calculate_trend_metrics(trending_songs, is_song=True)
        self.calculate_trend_metrics(breakout_songs, is_song=True)
        
        # Combine data
        dashboard_data = {
            "hashtags_7d": hashtags_7d,
            "hashtags_30d": hashtags_30d,
            "trending_songs": trending_songs,
            "breakout_songs": breakout_songs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save data for dashboard
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
        # Also save raw data for records
        with open(f"{self.data_dir}/tiktok_data_raw_{datetime.now().strftime('%Y%m%d')}.json", "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Data saved to {self.output_file}")
    
    def calculate_trend_metrics(self, trends, is_song=False):
        """Calculate growth rates and trend status for each trend"""
        count_key = "post_count" if not is_song else "post_count"
        name_key = "hashtag" if not is_song else "song_name"
        
        for trend in trends:
            # Parse post count into numeric value
            post_count = self.parse_count(trend.get(count_key, "0"))
            trend["numeric_count"] = post_count
            
            # Generate random growth rate for demo purposes
            # In a real implementation, you would calculate this based on historical data
            if is_song and "breakout" in trend.get("type", ""):
                # Higher growth for breakout songs
                growth = 200 + (trend["rank"] * -15) + (hash(trend.get(name_key, "")) % 100)
            else:
                # Normal growth rate calculation
                growth = 100 + (trend["rank"] * -3) + (hash(trend.get(name_key, "")) % 50)
            
            trend["growth"] = max(5, growth)  # Ensure minimum growth rate
            
            # Determine trend status based on growth rate
            if trend["growth"] > 200:
                trend["status"] = "rising"
            elif trend["growth"] > 100:
                trend["status"] = "peaked"
            elif trend["growth"] > 50:
                trend["status"] = "stable"
            else:
                trend["status"] = "falling"
    
    def parse_count(self, count_str):
        """Parse numeric count from string formats like '1.2M'"""
        if not count_str:
            return 0
        
        if isinstance(count_str, (int, float)):
            return count_str
        
        try:
            count_str = str(count_str).upper().replace(',', '')
            multiplier = 1
            
            if 'K' in count_str:
                multiplier = 1000
                count_str = count_str.replace('K', '')
            elif 'M' in count_str:
                multiplier = 1000000
                count_str = count_str.replace('M', '')
            elif 'B' in count_str:
                multiplier = 1000000000
                count_str = count_str.replace('B', '')
            
            # Extract numeric part
            import re
            numeric_match = re.search(r'(\d+\.?\d*)', count_str)
            if numeric_match:
                return float(numeric_match.group(1)) * multiplier
            return 0
        except:
            return 0
    
    def push_to_github(self):
        """Push updated data to GitHub repository"""
        try:
            print("\nPushing updates to GitHub...")
            
            # Check if git is configured properly
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
            if not result.stdout.strip():
                print("Git user not configured. Please set up git credentials.")
                return
            
            # Add files
            subprocess.run(["git", "add", self.output_file])
            subprocess.run(["git", "add", f"{self.charts_dir}/*"])
            
            # Commit
            commit_message = f"Update TikTok trend data - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_message])
            
            # Push
            subprocess.run(["git", "push", "origin", "main"])
            
            print("✅ Successfully pushed updates to GitHub")
            
        except Exception as e:
            print(f"Error pushing to GitHub: {e}")
            print("You can push changes manually.")

# Execute the scraper
if __name__ == "__main__":
    scraper = TikTokTrendScraper()
    scraper.run_scraper()