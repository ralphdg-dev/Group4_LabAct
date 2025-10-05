import requests
import urllib.parse
import sys
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored terminal text
init(autoreset=True)

class MapQuestEnhanced:
    def __init__(self):
        self.route_url = "https://graphhopper.com/api/1/route?"
        self.key = "560ec147-2865-4947-b87c-7d70228cbd08"
        self.unit_system = "metric"  # Default unit system
        self.vehicle_profiles = ["car", "bike", "foot"]
        
    def display_welcome(self):
        """Display welcome message and application header"""
        print(Fore.CYAN + "=" * 70)
        print(Fore.YELLOW + "🚗 MAPQUEST ENHANCED ROUTE PLANNER 🗺️")
        print(Fore.CYAN + "=" * 70)
        print(Fore.WHITE + "Plan your journey with detailed directions and multiple options!")
        print()
    
    def get_unit_preference(self):
        """Allow user to choose between metric and imperial units"""
        print(Fore.GREEN + "📏 UNIT SELECTION")
        print(Fore.CYAN + "-" * 40)
        print(Fore.WHITE + "1. Metric System (kilometers, meters)")
        print(Fore.WHITE + "2. Imperial System (miles, feet)")
        print(Fore.CYAN + "-" * 40)
        
        while True:
            choice = input(Fore.YELLOW + "Choose unit system (1 or 2): ").strip()
            if choice == "1":
                self.unit_system = "metric"
                print(Fore.GREEN + "✓ Metric system selected")
                break
            elif choice == "2":
                self.unit_system = "imperial"
                print(Fore.GREEN + "✓ Imperial system selected")
                break
            else:
                print(Fore.RED + "❌ Invalid choice. Please enter 1 or 2.")
        print()
    
    def format_distance(self, meters):
        """Format distance based on selected unit system"""
        if self.unit_system == "metric":
            if meters >= 1000:
                return f"{meters/1000:.1f} km"
            else:
                return f"{meters:.0f} m"
        else:  # imperial
            miles = meters / 1609.34
            if miles >= 0.1:
                return f"{miles:.1f} miles"
            else:
                feet = meters * 3.28084
                return f"{feet:.0f} ft"
    
    def format_time(self, milliseconds):
        """Format time duration in a readable format"""
        total_seconds = milliseconds / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes:02d}m {seconds:02d}s"
        elif minutes > 0:
            return f"{minutes}m {seconds:02d}s"
        else:
            return f"{seconds}s"
    
    def display_vehicle_options(self):
        """Display available vehicle profiles"""
        print(Fore.GREEN + "🚗 VEHICLE PROFILES")
        print(Fore.CYAN + "-" * 40)
        for i, profile in enumerate(self.vehicle_profiles, 1):
            icon = "🚗" if profile == "car" else "🚲" if profile == "bike" else "🚶"
            print(Fore.WHITE + f"{i}. {icon} {profile.capitalize()}")
        print(Fore.CYAN + "-" * 40)
    
    def geocoding(self, location):
        """Enhanced geocoding with better error handling"""
        if not location or location.strip() == "":
            print(Fore.RED + "❌ Error: Location cannot be empty")
            return None, None, None, None
        
        geocode_url = "https://graphhopper.com/api/1/geocode?"
        url = geocode_url + urllib.parse.urlencode({
            "q": location, 
            "limit": "1", 
            "key": self.key
        })
        
        try:
            print(Fore.BLUE + f"🔍 Searching for: {location}")
            replydata = requests.get(url, timeout=10)
            json_data = replydata.json()
            json_status = replydata.status_code
            
            if json_status == 200 and len(json_data["hits"]) != 0:
                lat = json_data["hits"][0]["point"]["lat"]
                lng = json_data["hits"][0]["point"]["lng"]
                name = json_data["hits"][0]["name"]
                value = json_data["hits"][0]["osm_value"]
                
                # Build location name with available information
                country = json_data["hits"][0].get("country", "")
                state = json_data["hits"][0].get("state", "")
                
                if state and country:
                    new_loc = f"{name}, {state}, {country}"
                elif country:
                    new_loc = f"{name}, {country}"
                else:
                    new_loc = name
                
                print(Fore.GREEN + f"✓ Found: {new_loc} ({value})")
                return json_status, lat, lng, new_loc
            else:
                if json_status != 200:
                    error_msg = json_data.get("message", "Unknown error")
                    print(Fore.RED + f"❌ Geocoding API Error {json_status}: {error_msg}")
                else:
                    print(Fore.RED + f"❌ No results found for: {location}")
                return None, None, None, None
                
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"❌ Network error: {str(e)}")
            return None, None, None, None
        except Exception as e:
            print(Fore.RED + f"❌ Unexpected error: {str(e)}")
            return None, None, None, None
    
    def display_route_summary(self, paths_data, orig_name, dest_name, vehicle):
        """Display formatted route summary"""
        if paths_data["paths"][0]["distance"] == 0:
            print(Fore.YELLOW + "⚠️  Start and end locations are the same!")
            return
        
        distance = paths_data["paths"][0]["distance"]
        time_ms = paths_data["paths"][0]["time"]
        
        print(Fore.CYAN + "=" * 70)
        print(Fore.YELLOW + f"📍 ROUTE SUMMARY: {orig_name} → {dest_name}")
        print(Fore.CYAN + "=" * 70)
        
        # Create formatted summary table
        summary_data = [
            ["Vehicle", f"{'🚗' if vehicle == 'car' else '🚲' if vehicle == 'bike' else '🚶'} {vehicle.upper()}"],
            ["Total Distance", self.format_distance(distance)],
            ["Estimated Time", self.format_time(time_ms)],
            ["Unit System", "Metric" if self.unit_system == "metric" else "Imperial"]
        ]
        
        for item in summary_data:
            print(Fore.WHITE + f"{item[0]:<20} {Fore.GREEN}{item[1]}")
        
        print(Fore.CYAN + "=" * 70)
    
    def display_detailed_directions(self, paths_data):
        """Display step-by-step directions in a formatted table"""
        instructions = paths_data["paths"][0]["instructions"]
        
        print(Fore.YELLOW + "📋 TURN-BY-TURN DIRECTIONS")
        print(Fore.CYAN + "-" * 70)
        print(Fore.WHITE + f"{'Step':<4} {'Instruction':<40} {'Distance':<15}")
        print(Fore.CYAN + "-" * 70)
        
        for i, instruction in enumerate(instructions, 1):
            text = instruction["text"]
            distance = self.format_distance(instruction["distance"])
            
            # Add icons based on instruction type
            icon = "🛑" if "arrived" in text.lower() else "↷" if "turn" in text.lower() else "↑" if "continue" in text.lower() else "📍"
            
            print(Fore.WHITE + f"{i:<4} {icon} {text:<37} {Fore.GREEN}{distance:<15}")
        
        print(Fore.CYAN + "-" * 70)
    
    def get_user_input(self, prompt, allow_quit=True):
        """Get user input with quit option"""
        quit_msg = Fore.MAGENTA + " (or 'quit' to exit)" if allow_quit else ""
        user_input = input(Fore.YELLOW + f"{prompt}{quit_msg}: ").strip()
        
        if allow_quit and user_input.lower() in ['quit', 'q', 'exit']:
            return None
        return user_input
    
    def main_flow(self):
        """Main application flow"""
        self.display_welcome()
        self.get_unit_preference()
        
        while True:
            print(Fore.CYAN + "\n" + "=" * 70)
            print(Fore.YELLOW + "🆕 NEW ROUTE PLANNING")
            print(Fore.CYAN + "=" * 70)
            
            # Vehicle selection
            self.display_vehicle_options()
            vehicle_input = self.get_user_input("Choose vehicle profile")
            if vehicle_input is None:
                break
            
            vehicle = vehicle_input.lower()
            if vehicle not in self.vehicle_profiles:
                print(Fore.YELLOW + "⚠️  Invalid vehicle profile. Using 'car' as default.")
                vehicle = "car"
            
            # Starting location
            start_loc = self.get_user_input("Starting location")
            if start_loc is None:
                break
            
            orig = self.geocoding(start_loc)
            if orig[0] is None:  # Error in geocoding
                print(Fore.RED + "❌ Please try again with a different starting location.")
                continue
            
            # Destination
            dest_loc = self.get_user_input("Destination")
            if dest_loc is None:
                break
            
            dest = self.geocoding(dest_loc)
            if dest[0] is None:  # Error in geocoding
                print(Fore.RED + "❌ Please try again with a different destination.")
                continue
            
            # Get route data
            print(Fore.BLUE + "\n📡 Calculating route...")
            try:
                op = "&point=" + str(orig[1]) + "%2C" + str(orig[2])
                dp = "&point=" + str(dest[1]) + "%2C" + str(dest[2])
                paths_url = self.route_url + urllib.parse.urlencode({
                    "key": self.key, 
                    "vehicle": vehicle
                }) + op + dp
                
                response = requests.get(paths_url, timeout=15)
                paths_status = response.status_code
                paths_data = response.json()
                
                if paths_status == 200:
                    self.display_route_summary(paths_data, orig[3], dest[3], vehicle)
                    self.display_detailed_directions(paths_data)
                else:
                    error_msg = paths_data.get("message", "Unknown routing error")
                    print(Fore.RED + f"❌ Routing API Error {paths_status}: {error_msg}")
                    
            except requests.exceptions.Timeout:
                print(Fore.RED + "❌ Request timeout. Please check your connection and try again.")
            except requests.exceptions.RequestException as e:
                print(Fore.RED + f"❌ Network error: {str(e)}")
            except Exception as e:
                print(Fore.RED + f"❌ Unexpected error: {str(e)}")
            
            # Ask if user wants to plan another route
            print(Fore.CYAN + "\n" + "=" * 70)
            continue_choice = self.get_user_input("Plan another route? (yes/no)", allow_quit=False)
            if continue_choice and continue_choice.lower() in ['no', 'n']:
                print(Fore.GREEN + "👋 Thank you for using MapQuest 2.0")
                break

def main():
    """Main entry point with error handling"""
    try:
        app = MapQuestEnhanced()
        app.main_flow()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n👋 Program interrupted by user. Goodbye!")
    except Exception as e:
        print(Fore.RED + f"💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()