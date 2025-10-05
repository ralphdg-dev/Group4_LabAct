import requests
import urllib.parse
import time
import sys

class GeocodingError(Exception):
    """Custom exception for geocoding errors"""
    pass

class RoutingError(Exception):
    """Custom exception for routing errors"""
    pass

def geocoding(location, key, max_retries=3):
    """
    Enhanced geocoding function with error handling and retry logic
    
    Args:
        location (str): Location to geocode
        key (str): API key
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        tuple: (status_code, lat, lng, formatted_location_name)
    """
    if not location or location.strip() == "":
        raise ValueError("Location cannot be empty")
    
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({
        "q": location, 
        "limit": "1", 
        "key": key,
        "locale": "en"  # Add locale for consistent results
    })
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)  # Add timeout
            response.raise_for_status()  # Raises HTTPError for bad status codes
            
            json_data = response.json()
            json_status = response.status_code
            
            # Validate response structure
            if "hits" not in json_data:
                raise GeocodingError("Invalid response format from geocoding API")
            
            if json_status == 200 and json_data.get("hits"):
                hit = json_data["hits"][0]
                lat = hit["point"]["lat"]
                lng = hit["point"]["lng"]
                name = hit.get("name", location)
                value = hit.get("osm_value", "unknown")
                
                # Enhanced location formatting
                country = hit.get("country", "")
                state = hit.get("state", "")
                city = hit.get("city", "")
                
                # Build formatted location name
                location_parts = [name]
                if city and city != name:
                    location_parts.append(city)
                if state:
                    location_parts.append(state)
                if country:
                    location_parts.append(country)
                
                new_loc = ", ".join(filter(None, location_parts))
                
                print(f"Geocoding API URL for {new_loc} (Location Type: {value})\n{url}")
                return json_status, lat, lng, new_loc
            else:
                if not json_data.get("hits"):
                    raise GeocodingError(f"No results found for location: {location}")
                else:
                    raise GeocodingError(f"Geocoding failed with status: {json_status}")
                    
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise GeocodingError(f"Network error after {max_retries} attempts: {str(e)}")
            time.sleep(1)  # Wait before retry
        except KeyError as e:
            raise GeocodingError(f"Unexpected response format: missing key {str(e)}")
    
    raise GeocodingError("Max retries exceeded")

def get_route(orig, dest, vehicle, key, max_retries=3):
    """
    Get route information between two points
    
    Args:
        orig: Origin coordinates (lat, lng)
        dest: Destination coordinates (lat, lng)
        vehicle: Vehicle profile
        key: API key
        max_retries: Maximum retry attempts
    
    Returns:
        dict: Route data
    """
    route_url = "https://graphhopper.com/api/1/route?"
    
    op = f"&point={orig[1]},{orig[2]}"
    dp = f"&point={dest[1]},{dest[2]}"
    
    paths_url = (route_url + urllib.parse.urlencode({
        "key": key, 
        "vehicle": vehicle,
        "instructions": "true",
        "calc_points": "true",
        "elevation": "false"
    }) + op + dp)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(paths_url, timeout=15)
            response.raise_for_status()
            
            paths_data = response.json()
            paths_status = response.status_code
            
            if paths_status == 200:
                return paths_data, paths_url
            else:
                error_msg = paths_data.get("message", "Unknown routing error")
                if attempt == max_retries - 1:
                    raise RoutingError(f"Routing failed: {error_msg}")
                time.sleep(1)
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise RoutingError(f"Network error after {max_retries} attempts: {str(e)}")
            time.sleep(1)
    
    raise RoutingError("Max retries exceeded for routing")

def format_duration(milliseconds):
    """Convert milliseconds to formatted time string"""
    seconds = int(milliseconds / 1000)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def format_distance(meters, unit_system="metric"):
    """Format distance with appropriate units"""
    if unit_system == "imperial":
        miles = meters / 1609.34
        return f"{miles:.1f} miles", miles
    else:
        km = meters / 1000
        return f"{km:.1f} km", km

def display_route_info(paths_data, orig_name, dest_name, vehicle):
    """Display formatted route information"""
    if not paths_data.get("paths"):
        print("No route found between the specified locations.")
        return
    
    path = paths_data["paths"][0]
    
    # Basic route information
    distance_m = path["distance"]
    duration_ms = path["time"]
    
    dist_metric, km = format_distance(distance_m, "metric")
    dist_imperial, miles = format_distance(distance_m, "imperial")
    duration_str = format_duration(duration_ms)
    
    print("=" * 60)
    print(f"Directions from {orig_name} to {dest_name} by {vehicle}")
    print("=" * 60)
    print(f"Distance: {dist_metric} ({dist_imperial})")
    print(f"Duration: {duration_str}")
    
    # Display elevation info if available
    if "ascend" in path and "descend" in path:
        print(f"Elevation: +{path['ascend']:.0f}m / -{path['descend']:.0f}m")
    
    print("=" * 60)
    
    # Turn-by-turn directions
    if "instructions" in path:
        print("Turn-by-turn directions:")
        print("-" * 40)
        
        for i, instruction in enumerate(path["instructions"]):
            text = instruction["text"]
            distance = instruction["distance"]
            _, dist_km = format_distance(distance, "metric")
            _, dist_miles = format_distance(distance, "imperial")
            
            print(f"{i+1:2d}. {text:50} ({dist_km:.1f} km / {dist_miles:.1f} mi)")
    
    print("=" * 60)

def get_user_input(prompt, options=None, allow_quit=True):
    """Get user input with validation"""
    while True:
        user_input = input(prompt).strip().lower()
        
        if allow_quit and user_input in ("quit", "q", "exit"):
            return None
        
        if options and user_input not in options:
            print(f"Invalid option. Please choose from: {', '.join(options)}")
            continue
            
        return user_input

def main():
    """Enhanced main function with better error handling and user experience"""
    # Consider moving API key to environment variable or config file
    key = "560ec147-2865-4947-b87c-7d70228cbd08"
    
    # Available vehicle profiles
    profiles = ["car", "bike", "foot", "scooter", "truck", "small_truck"]
    
    print("\n" + "🚗" + "=" * 50 + "🚗")
    print("          GRAPHHOPPER ROUTING APPLICATION")
    print("🚗" + "=" * 50 + "🚗")
    
    while True:
        try:
            # Vehicle selection
            print("\nAvailable vehicle profiles:")
            print("-" * 30)
            for profile in profiles:
                print(f"  • {profile}")
            print("-" * 30)
            
            vehicle = get_user_input(
                "Enter vehicle profile (or 'quit' to exit): ",
                options=profiles,
                allow_quit=True
            )
            
            if vehicle is None:
                print("Thank you for using the routing service. Goodbye!")
                break
            
            # Get locations
            orig_location = get_user_input("Starting Location: ", allow_quit=True)
            if orig_location is None:
                break
                
            dest_location = get_user_input("Destination: ", allow_quit=True)
            if dest_location is None:
                break
            
            print("\n" + "🔄 Geocoding locations..." + "🔍")
            
            # Geocode locations
            try:
                orig = geocoding(orig_location, key)
                dest = geocoding(dest_location, key)
            except (GeocodingError, ValueError) as e:
                print(f"❌ Geocoding error: {e}")
                continue
            
            if orig[0] != 200 or dest[0] != 200:
                print("❌ Failed to geocode one or both locations.")
                continue
            
            print("\n" + "🗺️  Calculating route..." + "⏱️")
            
            # Get route
            try:
                paths_data, paths_url = get_route(orig, dest, vehicle, key)
                
                print("✅ Routing API Status: Success")
                print(f"🔗 Routing API URL:\n{paths_url}")
                
                # Display route information
                display_route_info(paths_data, orig[3], dest[3], vehicle)
                
            except RoutingError as e:
                print(f"❌ Routing error: {e}")
                continue
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if input("Continue? (y/n): ").lower() != 'y':
                break

if __name__ == "__main__":
    main()