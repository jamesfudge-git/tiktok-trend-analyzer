#!/usr/bin/env python3
# scripts/tiktok_scraper.py
from seleniumbase import SB
import time
import json
import os
import subprocess
from datetime import datetime
from PIL import Image
import numpy as np
import re

class TikTokTrendScraper:
    """
    Unified TikTok trend scraper for hashtags and songs.
    Scrapes trending data from TikTok Creative Center.
    """
    def __init__(self):
        self.hashtag_url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        self.song_url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en"
        self.charts_dir = "charts"
        self.data_dir = "data"
        self.docs_dir = "docs"
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.charts_dir, self.data_dir, self.docs_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def run_full_scrape(self):
        """Run both hashtag and song scrapers and combine the data"""
        print(f"[{datetime.now()}] Starting full TikTok trend scrape...")
        start_time = time.time()
        
        # Run hashtag scraper
        hashtag_data = self.scrape_hashtags()
        
        # Run song scraper
        song_data = self.scrape_songs()
        
        # Combine the data
        combined_data = {
            "hashtags_7d": hashtag_data.get("hashtags_7d", []),
            "hashtags_30d": hashtag_data.get("hashtags_30d", []),
            "trending_songs": song_data.get("trending_songs", []),
            "breakout_songs": song_data.get("breakout_songs", []),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save combined data
        self.save_data(combined_data)
        
        # Push to GitHub
        self.push_to_github()
        
        # Report completion
        elapsed_time = time.time() - start_time
        print(f"[{datetime.now()}] Full scrape completed in {elapsed_time:.2f} seconds")
        print(f"Collected {len(combined_data['hashtags_7d'])} 7-day hashtags, {len(combined_data['hashtags_30d'])} 30-day hashtags")
        print(f"Collected {len(combined_data['trending_songs'])} trending songs, {len(combined_data['breakout_songs'])} breakout songs")
        
        return combined_data

    def scrape_hashtags(self):
        """Run the hashtag scraper to get hashtag trends"""
        print(f"[{datetime.now()}] Starting hashtag scraping...")
        
        with SB(uc=True) as sb:
            # Navigate to hashtag page
            sb.open(self.hashtag_url)
            sb.sleep(5)
            
            # Handle cookie consent
            try:
                sb.click("button[aria-label='Accept all cookies']", timeout=3)
            except:
                print("No cookie dialog found or already accepted")
            
            # First extract 7-day hashtags
            hashtags_7d = self.extract_hashtags(sb, "7d", 50)
            
            # Switch to 30-day view and extract those hashtags
            if self.switch_to_30day_view(sb):
                hashtags_30d = self.extract_hashtags(sb, "30d", 50)
            else:
                hashtags_30d = []
        
        # Calculate additional metrics
        self.calculate_hashtag_metrics(hashtags_7d, hashtags_30d)
        
        # Prepare result
        result = {
            "hashtags_7d": hashtags_7d,
            "hashtags_30d": hashtags_30d,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save hashtag data separately
        with open(f"{self.data_dir}/tiktok_hashtags.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"[{datetime.now()}] Hashtag scraping complete")
        print(f"7-day hashtags: {len(hashtags_7d)}")
        print(f"30-day hashtags: {len(hashtags_30d)}")
        
        return result
    
    def extract_hashtags(self, sb, period_name, target_count=50):
        """Extract hashtags for a time period with enhanced detail"""
        print(f"\nExtracting hashtags for {period_name} period (target: {target_count})...")
        hashtags = []
        max_attempts = 15
        attempt = 0
        
        while len(hashtags) < target_count and attempt < max_attempts:
            attempt += 1
            print(f"Extraction attempt {attempt}/{max_attempts}...")
            
            try:
                # Find hashtag elements
                hashtag_elements = sb.find_elements("[class*='CardPc_titleText']")
                print(f"Found {len(hashtag_elements)} potential hashtag elements")
                
                for i, element in enumerate(hashtag_elements):
                    if len(hashtags) >= target_count:
                        break
                        
                    try:
                        # Extract hashtag text
                        hashtag_text = element.text.strip()
                        if not hashtag_text or any(h['hashtag'] == hashtag_text for h in hashtags):
                            continue
                        
                        # Find parent container for additional data
                        try:
                            container = element.find_element("xpath", "./../../../..")
                        except:
                            print(f"  ⚠️ Could not find parent container for {hashtag_text}")
                            continue
                        
                        # Extract post count
                        post_count = None
                        try:
                            post_count_element = container.find_element("css selector", "span.CardPc_itemValue__XGDmG")
                            post_count = post_count_element.text.strip()
                        except Exception as e:
                            print(f"  ⚠️ Failed to get post count for '{hashtag_text}': {e}")
                        
                        # Extract chart image
                        chart_image = None
                        try:
                            sb.sleep(0.5)  # Slow down before finding canvas
                            canvas = container.find_element("css selector", "canvas")
                            if canvas:
                                safe_name = ''.join(c if c.isalnum() else '_' for c in hashtag_text[1:])
                                chart_filename = f"{self.charts_dir}/{period_name}_{len(hashtags)+1}_{safe_name}.png"
                                chart_image = self.capture_chart_screenshot(sb, canvas, chart_filename)
                        except Exception as e:
                            print(f"  ⚠️ Failed to capture chart for '{hashtag_text}': {e}")
                        
                        # Extract ranking status
                        ranking_status = self.extract_ranking_status(sb, container)
                        
                        # Create hashtag data object
                        hashtag_data = {
                            "hashtag": hashtag_text,
                            "post_count": post_count,
                            "chart_image": chart_image,
                            "rank": len(hashtags) + 1,
                            "timeframe": period_name,
                            "ranking_direction": ranking_status["direction"],
                            "ranking_change": ranking_status["change"]
                        }
                        
                        # Add to list
                        hashtags.append(hashtag_data)
                        print(f"  ✅ Collected: {hashtag_text} | Posts: {post_count} | Ranking Change: {ranking_status['direction']} {ranking_status['change']}")
                        
                        # Slow down between hashtags for stability
                        sb.sleep(0.5)
                        
                    except Exception as e:
                        print(f"  ❌ Error extracting hashtag {i+1}: {e}")
                
                print(f"Total unique hashtags so far: {len(hashtags)}/{target_count}")
                
                # Check if we need more hashtags
                if len(hashtags) < target_count:
                    sb.save_screenshot(f"debug_{period_name}_before_view_more_{attempt}.png")
                    print("Clicking 'View More' button...")
                    
                    view_more_selectors = [
                        "div[class*='ViewMoreBtn']",
                        "//div[text()='View more']",
                        "//button[contains(text(), 'View more')]",
                        "//div[contains(@class, 'ViewMoreBtn')]"
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
                        sb.save_screenshot(f"debug_{period_name}_failed_view_more_{attempt}.png")
                        
                        # Last resort: try JavaScript scroll
                        sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        print("Used JavaScript to scroll to bottom")
                        
                    # Wait longer after clicking View More
                    sb.sleep(3)
                    sb.execute_script("window.scrollBy(0, 500)")
                    sb.sleep(2)
                
                else:
                    break
                
            except Exception as e:
                print(f"Error during extraction attempt {attempt}: {e}")
                sb.save_screenshot(f"debug_{period_name}_error_{attempt}.png")
        
        return hashtags
    
    def capture_chart_screenshot(self, sb, element, filename, max_retries=3):
        """Capture chart screenshot with improved reliability and slower timing"""
        for attempt in range(max_retries):
            try:
                # Make sure the element is visible and pause
                sb.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
                sb.sleep(2)  # Longer wait for rendering and stability
                
                # Take screenshot
                element.screenshot(filename)
                
                # Verify screenshot is valid
                try:
                    img = Image.open(filename)
                    img_array = np.array(img)
                    
                    # Check if image is mostly black or single color
                    is_valid = True
                    if img_array.size > 0:
                        # Calculate percentage of black pixels
                        if len(img_array.shape) == 3:  # Color image
                            black_pixels = np.sum(np.all(img_array == [0, 0, 0], axis=2))
                        else:  # Grayscale
                            black_pixels = np.sum(img_array == 0)
                            
                        total_pixels = img_array.shape[0] * img_array.shape[1]
                        black_percentage = black_pixels / total_pixels
                        
                        if black_percentage > 0.9:
                            print(f"  ⚠️ Chart image is {black_percentage:.1%} black pixels")
                            is_valid = False
                            
                        # Check for variety of colors
                        if len(img_array.shape) == 3:
                            flattened = img_array.reshape(-1, img_array.shape[2])
                            unique_rows = np.unique(flattened, axis=0)
                            if len(unique_rows) < 10:
                                print(f"  ⚠️ Chart has only {len(unique_rows)} unique colors")
                                is_valid = False
                    
                    if is_valid:
                        print(f"  ✅ Captured valid chart image: {filename}")
                        return filename
                    else:
                        print(f"  ⚠️ Chart image appears invalid (mostly single color)")
                        # Keep the file for now in case it's useful for debugging
                except Exception as e:
                    print(f"  ⚠️ Error validating image: {e}")
                    
            except Exception as e:
                print(f"  ❌ Error capturing screenshot (attempt {attempt+1}): {e}")
            
            # Wait longer between attempts
            sb.sleep(3)
        
        print(f"  ❌ Failed to capture valid chart after {max_retries} attempts")
        return None
    
    def extract_ranking_status(self, sb, container):
        """Extract ranking change status (up/down and change value)"""
        status = {
            "direction": "stable",
            "change": 0
        }
        
        try:
            # Try to find ranking change indicator (arrow)
            try:
                # Check for up arrow (green)
                up_arrows = container.find_elements("css selector", "svg path[stroke='#5CA537']")
                if up_arrows and len(up_arrows) > 0:
                    status["direction"] = "up"
                else:
                    # Check for down arrow (red)
                    down_arrows = container.find_elements("css selector", "svg path[stroke='#FE334E']")
                    if down_arrows and len(down_arrows) > 0:
                        status["direction"] = "down"
                    else:
                        # Try alternate class-based selectors for arrows
                        up_indicators = container.find_elements("css selector", "[class*='arrow-up']")
                        if up_indicators and len(up_indicators) > 0:
                            status["direction"] = "up"
                        else:
                            down_indicators = container.find_elements("css selector", "[class*='arrow-down']")
                            if down_indicators and len(down_indicators) > 0:
                                status["direction"] = "down"
            except Exception as e:
                print(f"  ⚠️ Error finding ranking direction: {e}")
            
            # Try to find ranking change value
            try:
                # Multiple potential classes for ranking value
                selectors = [
                    "[class*='rankingvalueNum']",
                    "[class*='RankingStatus_rankingvalueNum']",
                    "[class*='RankingValue']",
                    "span.CardPc_rankingvalueNum__"
                ]
                
                for selector in selectors:
                    value_elements = container.find_elements("css selector", selector)
                    if value_elements and len(value_elements) > 0:
                        change_text = value_elements[0].text.strip()
                        if change_text and change_text.isdigit():
                            status["change"] = int(change_text)
                            break
            except Exception as e:
                print(f"  ⚠️ Error finding ranking change value: {e}")
                
        except Exception as e:
            print(f"  ⚠️ Error extracting ranking status: {e}")
            
        return status
    
    def switch_to_30day_view(self, sb):
        """Switch to 30-day view from default 7-day view"""
        print("\nSwitching to 30-day view...")
        try:
            # Scroll to top and pause
            sb.execute_script("window.scrollTo(0, 0)")
            sb.sleep(2)
            
            # Click dropdown
            try:
                sb.click("#hashtagPeriodSelect > span > div > div > div", timeout=5)
                print("Clicked period dropdown")
                sb.sleep(2)
                
                # Click "Last 30 days" option
                selectors = [
                    "//div[contains(@class, 'creative-component-single-line') and text()='Last 30 days']",
                    "//div[text()='Last 30 days']",
                    "//div[contains(text(), 'Last 30 days')]"
                ]
                
                clicked = False
                for selector in selectors:
                    try:
                        sb.click(selector, by="xpath", timeout=3)
                        clicked = True
                        print(f"✅ Clicked '30 days' option using: {selector}")
                        break
                    except Exception as e:
                        print(f"Failed to click with selector '{selector}': {e}")
                
                if not clicked:
                    print("❌ Could not click '30 days' option")
                    return False
                
                # Wait for page to update
                sb.sleep(5)
                sb.save_screenshot("after_switching_to_30d.png")
                return True
                
            except Exception as e:
                print(f"❌ Error clicking period dropdown: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error switching to 30-day view: {e}")
            return False
    
    def calculate_hashtag_metrics(self, hashtags_7d, hashtags_30d):
        """Calculate additional metrics like growth rate, trend status"""
        print("\nCalculating hashtag metrics...")
        
        # Set up hashtag lookup maps
        hashtags_7d_map = {h["hashtag"]: h for h in hashtags_7d}
        hashtags_30d_map = {h["hashtag"]: h for h in hashtags_30d}
        
        # Calculate metrics for 7-day hashtags
        for hashtag in hashtags_7d:
            # Default growth and status
            hashtag["growth_rate"] = 0
            hashtag["trend_status"] = "stable"
            
            # Set numeric post count
            hashtag["numeric_post_count"] = self.parse_count(hashtag["post_count"])
            
            # Analyze ranking change
            if hashtag["ranking_direction"] == "up":
                change_value = hashtag["ranking_change"]
                if change_value > 10:
                    hashtag["trend_status"] = "rising"
                elif change_value > 5:
                    hashtag["trend_status"] = "trending"
            elif hashtag["ranking_direction"] == "down":
                change_value = hashtag["ranking_change"]
                if change_value > 10:
                    hashtag["trend_status"] = "falling"
                    
            # Check if in 30-day data for cross-timeframe analysis
            if hashtag["hashtag"] in hashtags_30d_map:
                h30 = hashtags_30d_map[hashtag["hashtag"]]
                
                # Compare rankings between timeframes
                rank7 = hashtag["rank"]
                rank30 = h30["rank"]
                
                if rank7 < rank30:
                    hashtag["period_momentum"] = "accelerating"
                elif rank7 > rank30:
                    hashtag["period_momentum"] = "decelerating"
                else:
                    hashtag["period_momentum"] = "steady"
                    
                # Compare post counts if available
                if hashtag["numeric_post_count"] > 0 and "numeric_post_count" in h30 and h30["numeric_post_count"] > 0:
                    period_growth = ((hashtag["numeric_post_count"] - h30["numeric_post_count"]) / h30["numeric_post_count"]) * 100
                    hashtag["period_growth_pct"] = round(period_growth, 2)
            else:
                hashtag["period_momentum"] = "new"
        
        # Calculate metrics for 30-day hashtags
        for hashtag in hashtags_30d:
            # Set numeric post count
            hashtag["numeric_post_count"] = self.parse_count(hashtag["post_count"])
            
            # Analyze ranking change
            if hashtag["ranking_direction"] == "up":
                change_value = hashtag["ranking_change"]
                if change_value > 10:
                    hashtag["trend_status"] = "rising"
                elif change_value > 5:
                    hashtag["trend_status"] = "trending"
            elif hashtag["ranking_direction"] == "down":
                change_value = hashtag["ranking_change"]
                if change_value > 10:
                    hashtag["trend_status"] = "falling"
                else:
                    hashtag["trend_status"] = "stable"
            else:
                hashtag["trend_status"] = "stable"
                
    def scrape_songs(self):
        """Run the song scraper to get song trends"""
        print(f"[{datetime.now()}] Starting song scraping...")
        
        with SB(uc=True) as sb:
            # Navigate to songs page
            sb.open(self.song_url)
            sb.sleep(5)
            
            # Handle cookie consent
            try:
                sb.click("button[aria-label='Accept all cookies']", timeout=3)
            except:
                print("No cookie dialog found or already accepted")
            
            # Extract trending songs
            trending_songs = self.extract_songs(sb, "trending", 20)
            
            # Switch to breakout tab and extract those songs
            if self.switch_to_breakout_songs(sb):
                breakout_songs = self.extract_songs(sb, "breakout", 10)
            else:
                breakout_songs = []
        
        # Apply additional song metrics
        self.calculate_song_metrics(trending_songs, breakout_songs)
        
        # Prepare result
        result = {
            "trending_songs": trending_songs,
            "breakout_songs": breakout_songs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save song data separately
        with open(f"{self.data_dir}/tiktok_songs.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"[{datetime.now()}] Song scraping complete")
        print(f"Trending songs: {len(trending_songs)}")
        print(f"Breakout songs: {len(breakout_songs)}")
        
        return result
    
    def extract_songs(self, sb, section_name, target_count=20):
        """Extract songs for the specified section"""
        print(f"\nExtracting {section_name} songs (target: {target_count})...")
        songs = []
        max_attempts = 10
        attempt = 0
        
        while len(songs) < target_count and attempt < max_attempts:
            attempt += 1
            print(f"Extraction attempt {attempt}/{max_attempts}...")
            
            try:
                # Find song elements
                song_cards = sb.find_elements("div[class*='ItemCard_infoContentContainer']")
                print(f"Found {len(song_cards)} song cards")
                
                for i, card in enumerate(song_cards):
                    if len(songs) >= target_count:
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
                            print(f"  ⚠️ Failed to get song name for card {i+1}")
                            continue
                        
                        # Skip if song already exists in list
                        if any(s['song_name'] == song_name for s in songs):
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
                        chart_image = None
                        try:
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
                                sb.sleep(0.5)  # Slow down for stability
                                safe_song_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in song_name)
                                chart_filename = f"{self.charts_dir}/song_{section_name}_{len(songs)+1}_{safe_song_name[:30]}.png"
                                chart_image = self.capture_chart_screenshot(sb, canvas, chart_filename)
                        except Exception as e:
                            print(f"  ⚠️ Failed to capture chart for '{song_name}': {e}")
                        
                        # Extract ranking status
                        ranking_status = {"direction": "stable", "change": 0}
                        try:
                            # Check for ranking indicators
                            ranking_elements = card.find_elements("css selector", "[class*='RankingStatus']")
                            if ranking_elements:
                                # Check for up arrow (green)
                                up_arrows = card.find_elements("css selector", "svg path[stroke='#5CA537']")
                                if up_arrows and len(up_arrows) > 0:
                                    ranking_status["direction"] = "up"
                                else:
                                    # Check for down arrow (red)
                                    down_arrows = card.find_elements("css selector", "svg path[stroke='#FE334E']")
                                    if down_arrows and len(down_arrows) > 0:
                                        ranking_status["direction"] = "down"
                                
                                # Try to find ranking change value
                                value_elements = card.find_elements("css selector", "[class*='rankingvalueNum']")
                                if value_elements and len(value_elements) > 0:
                                    change_text = value_elements[0].text.strip()
                                    if change_text and change_text.isdigit():
                                        ranking_status["change"] = int(change_text)
                        except Exception as e:
                            print(f"  ⚠️ Error extracting ranking status for '{song_name}': {e}")
                        
                        # Create song data object
                        song_data = {
                            "song_name": song_name,
                            "artist": artist_name,
                            "post_count": post_count,
                            "chart_image": chart_image,
                            "rank": len(songs) + 1,
                            "type": section_name,
                            "ranking_direction": ranking_status["direction"],
                            "ranking_change": ranking_status["change"]
                        }
                        
                        # Add to list
                        songs.append(song_data)
                        print(f"  ✅ Collected: {song_name} by {artist_name or 'Unknown'} | Posts: {post_count}")
                        
                        # Slow down between songs for stability
                        sb.sleep(0.5)
                        
                    except Exception as e:
                        print(f"  ❌ Error extracting song {i+1}: {e}")
                
                print(f"Total unique songs so far: {len(songs)}/{target_count}")
                
                # Check if we need more songs
                if len(songs) < target_count:
                    sb.save_screenshot(f"debug_songs_{section_name}_before_view_more_{attempt}.png")
                    print("Clicking 'View More' button...")
                    
                    view_more_selectors = [
                        "div[class*='ViewMoreBtn']",
                        "//div[text()='View more']",
                        "//button[contains(text(), 'View more')]",
                        "//div[contains(@class, 'ViewMoreBtn')]"
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
                        sb.save_screenshot(f"debug_songs_{section_name}_failed_view_more_{attempt}.png")
                        
                        # Last resort: try JavaScript scroll
                        sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        print("Used JavaScript to scroll to bottom")
                        
                    # Wait longer after clicking View More
                    sb.sleep(3)
                    sb.execute_script("window.scrollBy(0, 500)")
                    sb.sleep(2)
                
                else:
                    break
                
            except Exception as e:
                print(f"Error during song extraction attempt {attempt}: {e}")
                sb.save_screenshot(f"debug_songs_{section_name}_error_{attempt}.png")
        
        return songs
    
    def switch_to_breakout_songs(self, sb):
        """Switch to Breakout Songs tab from Trending Songs tab"""
        print("\nSwitching to Breakout Songs tab...")
        try:
            # Scroll to top and pause
            sb.execute_script("window.scrollTo(0, 0)")
            sb.sleep(2)
            
            # Try different selectors for the Breakout tab
            breakout_selectors = [
                ".ContentTab_itemLabelText__hiCCd",
                "//span[text()='Breakout']",
                "//div[contains(@class, 'ContentTab_container')]//span[contains(text(), 'Breakout')]",
                "//div[contains(@class, 'ContentTab_item')]//span[contains(text(), 'Breakout')]",
                "//div[contains(@class, 'ContentTab')]//span[text()='Breakout']",
                "//span[contains(text(), 'Breakout')]"
            ]
            
            clicked = False
            for selector in breakout_selectors:
                try:
                    if selector.startswith("//"):
                        elements = sb.find_elements(selector, by="xpath")
                    else:
                        elements = sb.find_elements(selector)
                    
                    for elm in elements:
                        if 'Breakout' in elm.text:
                            elm.click()
                            clicked = True
                            print(f"✅ Clicked Breakout tab using selector: {selector}")
                            sb.sleep(5)
                            break
                    
                    if clicked:
                        break
                except Exception as e:
                    print(f"Failed to click with selector '{selector}': {e}")
            
            # If none of the above worked, try JavaScript click
            if not clicked:
                try:
                    sb.execute_script("Array.from(document.querySelectorAll('span')).find(el => el.innerText.includes('Breakout')).click()")
                    print("Used JavaScript to click Breakout tab")
                    clicked = True
                    sb.sleep(5)
                except Exception as e:
                    print(f"Failed to click Breakout tab using JavaScript: {e}")
            
            if not clicked:
                print("❌ Could not click Breakout tab")
                return False
            
            # Wait for page to update
            sb.sleep(5)
            sb.save_screenshot("after_switching_to_breakout.png")
            return True
                
        except Exception as e:
            print(f"❌ Error switching to Breakout Songs tab: {e}")
            return False
    
    def calculate_song_metrics(self, trending_songs, breakout_songs):
        """Calculate additional metrics for songs"""
        print("\nCalculating song metrics...")
        
        # Process trending songs
        for song in trending_songs:
            # Set numeric post count
            song["numeric_post_count"] = self.parse_count(song["post_count"])
            
            # Set lifecycle stage based on ranking direction and change
            if song["ranking_direction"] == "up" and song["ranking_change"] > 5:
                song["lifecycle_stage"] = "rising"
            elif song["ranking_direction"] == "down" and song["ranking_change"] > 5:
                song["lifecycle_stage"] = "declining"
            else:
                song["lifecycle_stage"] = "stable"
                
            # Set categories for songs
            song["categories"] = ["entertainment", "music"]
        
        # Process breakout songs
        for song in breakout_songs:
            # Set numeric post count
            song["numeric_post_count"] = self.parse_count(song["post_count"])
            
            # Breakout songs are always rising
            song["lifecycle_stage"] = "rising"
            
            # Set categories for songs
            song["categories"] = ["entertainment", "music"]
    
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
            numeric_match = re.search(r'(\d+\.?\d*)', count_str)
            if numeric_match:
                return float(numeric_match.group(1)) * multiplier
            return 0
        except:
            return 0
    
    def save_data(self, data):
        """Save the combined data to JSON files"""
        print(f"[{datetime.now()}] Saving trend data...")
        
        # Save to data directory for records
        raw_data_path = f"{self.data_dir}/tiktok_trends_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(raw_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Save as current data
        current_data_path = f"{self.data_dir}/current_data.json"
        with open(current_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Save to docs directory for dashboard
        dashboard_data_path = f"{self.docs_dir}/trendData.json"
        with open(dashboard_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Data saved to {dashboard_data_path}")
        return True
    
    def push_to_github(self):
        """Push changes to GitHub"""
        try:
            print(f"[{datetime.now()}] Pushing changes to GitHub...")
            
            # Check if git is configured properly
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
            if not result.stdout.strip():
                print("Git user not configured. Please set up git credentials.")
                return False
                
            # Check git status to see what's changed
            status_output = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            
            if not status_output:
                print("No changes detected in git")
                return True
                
            # Add specific files only
            files_to_add = [
                f"{self.docs_dir}/trendData.json",
                f"{self.data_dir}/current_data.json",
                f"{self.data_dir}/tiktok_hashtags.json",
                f"{self.data_dir}/tiktok_songs.json"
            ]
            
            # Add chart files if they exist
            chart_files = list(Path(self.charts_dir).glob("*"))
            if chart_files:
                files_to_add.append(f"{self.charts_dir}/*")
            
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
            commit_message = f"Update TikTok trend data - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            
            # Push
            subprocess.run(["git", "push", "origin", "main"], check=True)
            
            print("✅ Successfully pushed updates to GitHub")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error in git operations: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error in git operations: {e}")
            return False

# Run the scraper if executed directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TikTok Trend Scraper")
    parser.add_argument("--hashtags-only", action="store_true", help="Only scrape hashtags")
    parser.add_argument("--songs-only", action="store_true", help="Only scrape songs")
    parser.add_argument("--no-push", action="store_true", help="Don't push to GitHub")
    
    args = parser.parse_args()
    
    scraper = TikTokTrendScraper()
    
    if args.hashtags_only:
        hashtag_data = scraper.scrape_hashtags()
        if not args.no_push:
            scraper.push_to_github()
    elif args.songs_only:
        song_data = scraper.scrape_songs()
        if not args.no_push:
            scraper.push_to_github()
    else:
        # Run full scrape
        data = scraper.run_full_scrape()