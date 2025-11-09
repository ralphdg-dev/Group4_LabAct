import os
from dotenv import load_dotenv
import customtkinter as ctk
import tkinter
import requests
import urllib.parse
import threading
from PIL import Image, ImageTk
from io import BytesIO

# =======================================================================================
# SECTION 1: API LOGIC
# =======================================================================================

load_dotenv()
GRAPHOPPER_API_KEY = os.getenv("GRAPHHOPPER_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

class RouteAPI:
    def __init__(self):
        self.route_url = "https://graphhopper.com/api/1/route?"
        self.geocode_url = "https://graphhopper.com/api/1/geocode?"
        self.key = GRAPHOPPER_API_KEY
    
    def validate_api_key(self):
        if not self.key:
            return {"status": "error", "message": "API key not found. Please check your .env file."}
        if not isinstance(self.key, str) or len(self.key.strip()) == 0:
            return {"status": "error", "message": "Invalid API key format."}
        return {"status": "success"}
    
    def validate_location_input(self, location):
        if not location or not location.strip():
            return {"status": "error", "message": "Location cannot be empty."}
        if len(location.strip()) < 2:
            return {"status": "error", "message": "Location must be at least 2 characters long."}
        if len(location) > 200:
            return {"status": "error", "message": "Location is too long (max 200 characters)."}
        if any(char in location for char in ['<', '>', ';', '|', '&', '$']):
            return {"status": "error", "message": "Invalid characters in location."}
        return {"status": "success"}
    
    def validate_vehicle_type(self, vehicle):
        valid_vehicles = ['car', 'bike', 'foot']
        if vehicle not in valid_vehicles:
            return {"status": "error", "message": f"Invalid vehicle type. Must be one of: {', '.join(valid_vehicles)}"}
        return {"status": "success"}

    def geocode(self, location):
        validation_result = self.validate_location_input(location)
        if validation_result["status"] == "error":
            return validation_result
        api_key_check = self.validate_api_key()
        if api_key_check["status"] == "error":
            return api_key_check
        url = self.geocode_url + urllib.parse.urlencode({
            "q": location,
            "limit": "1",
            "key": self.key
        })
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {"status": "error", "message": f"API returned status code: {response.status_code}"}
            data = response.json()
            if data.get("hits"):
                point = data["hits"][0]["point"]
                name = data["hits"][0].get("name", "Unknown")
                country = data["hits"][0].get("country", "")
                state = data["hits"][0].get("state", "")
                full_name = f"{name}, {state}, {country}".strip(", ")
                return {"status": "success", "lat": point["lat"], "lng": point["lng"], "name": full_name}
            else:
                return {"status": "error", "message": f"No results found for '{location}'"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

    def get_route(self, start_coords, end_coords, vehicle):
        if not all(isinstance(coord, dict) for coord in [start_coords, end_coords]):
            return {"status": "error", "message": "Invalid coordinate data."}
        if not all(key in start_coords for key in ['lat', 'lng']) or not all(key in end_coords for key in ['lat', 'lng']):
            return {"status": "error", "message": "Missing coordinate data."}
        if not all(-90 <= coord['lat'] <= 90 and -180 <= coord['lng'] <= 180 for coord in [start_coords, end_coords]):
            return {"status": "error", "message": "Invalid coordinate values."}
        vehicle_validation = self.validate_vehicle_type(vehicle)
        if vehicle_validation["status"] == "error":
            return vehicle_validation
        api_key_check = self.validate_api_key()
        if api_key_check["status"] == "error":
            return api_key_check
        op = f"&point={start_coords['lat']},{start_coords['lng']}"
        dp = f"&point={end_coords['lat']},{end_coords['lng']}"
        url = self.route_url + urllib.parse.urlencode({"key": self.key, "vehicle": vehicle, "points_encoded": "false"}) + op + dp
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                return {"status": "error", "message": f"Routing API returned status code: {response.status_code}"}
            data = response.json()
            if 'paths' not in data or not data['paths']:
                return {"status": "error", "message": "No route path found in response."}
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected routing error: {str(e)}"}

    def get_static_map_url(self, start_coords, end_coords, route_points=None, width=900, height=450):
        """Generate a Google Static Maps URL with the actual route path from GraphHopper."""
        if not GOOGLE_MAPS_API_KEY:
            return None
        
        start = f"{start_coords['lat']},{start_coords['lng']}"
        end = f"{end_coords['lat']},{end_coords['lng']}"
        
        # Markers for start and end points
        markers = f"markers=color:0x1976D2|label:A|{start}&markers=color:0xD32F2F|label:B|{end}"
        
        # Build path from route points if available
        if route_points and len(route_points) > 0:
            # Google Maps Static API has URL length limitations
            # Simplify path by sampling points if there are too many
            max_points = 100  # Limit to avoid URL length issues
            if len(route_points) > max_points:
                # Sample points evenly across the route
                step = len(route_points) // max_points
                sampled_points = route_points[::step]
                # Always include the last point
                if route_points[-1] not in sampled_points:
                    sampled_points.append(route_points[-1])
                route_points = sampled_points
            
            # Build the path string with all route points
            path_coords = "|".join([f"{pt[1]},{pt[0]}" for pt in route_points])  # Note: lat,lng format
            path = f"path=color:0x2196F3|weight:5|{path_coords}"
        else:
            # Fallback to straight line if no route points available
            path = f"path=color:0x2196F3|weight:5|{start}|{end}"
        
        url = f"https://maps.googleapis.com/maps/api/staticmap?size={width}x{height}&{markers}&{path}&key={GOOGLE_MAPS_API_KEY}"
        return url

# =======================================================================================
# SECTION 2: GUI APPLICATION
# =======================================================================================

class FantasticRouterApp(ctk.CTk):
    def __init__(self, api_logic):
        super().__init__()
        self.api_logic = api_logic
        self.is_calculating = False
        
        # Premium Color Palette
        self.PRIMARY_BLUE = "#1565C0"
        self.DARK_BLUE = "#0D47A1"
        self.LIGHT_BLUE = "#42A5F5"
        self.ACCENT_ORANGE = "#FF6F00"
        self.HOVER_ORANGE = "#FF8F00"
        self.BG_GRADIENT_START = "#E3F2FD"
        self.BG_GRADIENT_END = "#F5F5F5"
        self.BG_WHITE = "#FFFFFF"
        self.TEXT_DARK = "#212121"
        self.TEXT_SECONDARY = "#616161"
        self.TEXT_LIGHT = "#FFFFFF"
        self.CARD_BG = "#FAFAFA"
        self.SUCCESS = "#4CAF50"
        self.ERROR = "#F44336"
        self.BORDER_LIGHT = "#E0E0E0"
        self.SHADOW_COLOR = "#90A4AE"

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        
        self.title("Fantastic Tour - Premium Route Planner")
        self.geometry("1300x850")
        self.minsize(1200, 750)
        self.configure(fg_color=self.BG_GRADIENT_START)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header_frame()
        self.create_main_content_frame()
        self.create_status_bar()

    # ---------------------------- HEADER FRAME ----------------------------

    def create_header_frame(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.PRIMARY_BLUE, corner_radius=0, height=110)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(0, weight=1)
        
        content_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=50, pady=25)
        
        left_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_section.pack(side="left", fill="y")
        
        # Logo with better styling
        try:
            logo_image = ctk.CTkImage(Image.open("f4_logo.png"), size=(55, 55))
            logo_label = ctk.CTkLabel(left_section, image=logo_image, text="")
            logo_label.pack(side="left", padx=(0, 20))
        except FileNotFoundError:
            logo_frame = ctk.CTkFrame(left_section, width=55, height=55, 
                                     fg_color=self.DARK_BLUE, corner_radius=27)
            logo_frame.pack(side="left", padx=(0, 20))
            logo_frame.pack_propagate(False)
            ctk.CTkLabel(logo_frame, text="F4", font=ctk.CTkFont(size=22, weight="bold"),
                        text_color=self.TEXT_LIGHT).place(relx=0.5, rely=0.5, anchor="center")
        
        # Title with enhanced styling
        title_section = ctk.CTkFrame(left_section, fg_color="transparent")
        title_section.pack(side="left")
        ctk.CTkLabel(title_section, text="FANTASTIC TOUR",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(anchor="w")
        ctk.CTkLabel(title_section, text="Advanced Route Planning & Navigation System",
                    font=ctk.CTkFont(size=14),
                    text_color=self.LIGHT_BLUE).pack(anchor="w", pady=(2, 0))

    # ---------------------------- MAIN CONTENT ----------------------------

    def create_main_content_frame(self):
        main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=35, pady=25)
        main_frame.grid_columnconfigure(0, weight=2, minsize=450)
        main_frame.grid_columnconfigure(1, weight=3, minsize=700)
        main_frame.grid_rowconfigure(0, weight=1)

        self.create_input_panel(main_frame)
        self.create_output_panel(main_frame)

    def create_input_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=self.BG_WHITE, corner_radius=15, 
                            border_width=0)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20), pady=(0, 0))
        panel.grid_columnconfigure(0, weight=1)
        
        # Elegant Header
        header = ctk.CTkFrame(panel, fg_color=self.PRIMARY_BLUE, corner_radius=12, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(25, 20))
        ctk.CTkLabel(header, text="🎯 Route Configuration", 
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(pady=15)
        
        # Origin Section with enhanced design
        origin_section = ctk.CTkFrame(panel, fg_color="transparent")
        origin_section.grid(row=1, column=0, sticky="ew", padx=25, pady=(15, 10))
        origin_section.grid_columnconfigure(0, weight=1)
        
        origin_label_frame = ctk.CTkFrame(origin_section, fg_color="transparent")
        origin_label_frame.grid(row=0, column=0, sticky="w", pady=(0, 10))
        ctk.CTkLabel(origin_label_frame, text="🏢", font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(origin_label_frame, text="Starting Point", 
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(side="left")
        
        self.start_entry = ctk.CTkEntry(origin_section, 
                                       placeholder_text="Enter starting location (e.g., Manila, Philippines)",
                                       height=50,
                                       font=ctk.CTkFont(size=14),
                                       border_width=2,
                                       border_color=self.BORDER_LIGHT,
                                       fg_color=self.CARD_BG,
                                       corner_radius=10)
        self.start_entry.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        # Destination Section
        dest_section = ctk.CTkFrame(panel, fg_color="transparent")
        dest_section.grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 10))
        dest_section.grid_columnconfigure(0, weight=1)
        
        dest_label_frame = ctk.CTkFrame(dest_section, fg_color="transparent")
        dest_label_frame.grid(row=0, column=0, sticky="w", pady=(0, 10))
        ctk.CTkLabel(dest_label_frame, text="📍", font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(dest_label_frame, text="Destination", 
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(side="left")
        
        self.end_entry = ctk.CTkEntry(dest_section, 
                                     placeholder_text="Enter destination (e.g., Makati City, Philippines)",
                                     height=50,
                                     font=ctk.CTkFont(size=14),
                                     border_width=2,
                                     border_color=self.BORDER_LIGHT,
                                     fg_color=self.CARD_BG,
                                     corner_radius=10)
        self.end_entry.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        
        # Vehicle Selection with premium design
        vehicle_frame = ctk.CTkFrame(panel, fg_color=self.CARD_BG, corner_radius=12,
                                    border_width=2, border_color=self.BORDER_LIGHT)
        vehicle_frame.grid(row=3, column=0, sticky="ew", padx=25, pady=(15, 20))
        
        vehicle_header = ctk.CTkFrame(vehicle_frame, fg_color="transparent")
        vehicle_header.pack(fill="x", padx=25, pady=(20, 15))
        ctk.CTkLabel(vehicle_header, text="🚗 Transportation Mode", 
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(anchor="w")
        
        self.vehicle_var = tkinter.StringVar(value="car")
        
        vehicles = [
            ("🚗 Car", "car", "Fastest route for driving"),
            ("🚲 Bicycle", "bike", "Bike-friendly paths"),
            ("🚶 Walking", "foot", "Pedestrian routes")
        ]
        
        for text, value, desc in vehicles:
            option_container = ctk.CTkFrame(vehicle_frame, fg_color="transparent")
            option_container.pack(fill="x", padx=20, pady=8)
            
            option_frame = ctk.CTkFrame(option_container, fg_color="transparent")
            option_frame.pack(anchor="w")
            
            ctk.CTkRadioButton(option_frame, text=text, variable=self.vehicle_var, value=value,
                             font=ctk.CTkFont(size=14, weight="bold"),
                             fg_color=self.PRIMARY_BLUE,
                             hover_color=self.LIGHT_BLUE,
                             text_color=self.TEXT_DARK).pack(side="left")
            
            ctk.CTkLabel(option_container, text=desc,
                        font=ctk.CTkFont(size=12),
                        text_color=self.TEXT_SECONDARY).pack(anchor="w", padx=(30, 0))
        
        # Spacer
        ctk.CTkFrame(vehicle_frame, fg_color="transparent", height=10).pack()
        
        # Premium Calculate Button
        button_container = ctk.CTkFrame(panel, fg_color="transparent")
        button_container.grid(row=4, column=0, sticky="ew", padx=25, pady=(25, 30))
        
        self.get_route_button = ctk.CTkButton(
            button_container,
            text="🚀 CALCULATE ROUTE",
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=self.ACCENT_ORANGE,
            hover_color=self.HOVER_ORANGE,
            height=60,
            corner_radius=12,
            command=self.start_route_calculation
        )
        self.get_route_button.pack(fill="x")

    # ---------------------------- OUTPUT PANEL ----------------------------

    def create_output_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=self.BG_WHITE, corner_radius=15)
        panel.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        panel.grid_rowconfigure(3, weight=0)
        panel.grid_rowconfigure(5, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(panel, fg_color=self.PRIMARY_BLUE, corner_radius=12, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(25, 20))
        ctk.CTkLabel(header, text="📊 Route Information & Map", 
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(pady=15)
        
        # Enhanced Summary Cards
        summary_container = ctk.CTkFrame(panel, fg_color="transparent")
        summary_container.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 20))
        summary_container.grid_columnconfigure((0, 1), weight=1)
        
        # Distance Card
        distance_card = ctk.CTkFrame(summary_container, fg_color=self.CARD_BG, 
                                    corner_radius=12, border_width=2, border_color=self.BORDER_LIGHT)
        distance_card.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(distance_card, text="📏 Total Distance", 
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=self.TEXT_SECONDARY).pack(pady=(20, 8))
        self.distance_label = ctk.CTkLabel(distance_card, text="-- km",
                                         font=ctk.CTkFont(size=28, weight="bold"),
                                         text_color=self.PRIMARY_BLUE)
        self.distance_label.pack(pady=(0, 20))
        
        # Time Card
        time_card = ctk.CTkFrame(summary_container, fg_color=self.CARD_BG, 
                                corner_radius=12, border_width=2, border_color=self.BORDER_LIGHT)
        time_card.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        ctk.CTkLabel(time_card, text="⏱️ Estimated Time", 
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=self.TEXT_SECONDARY).pack(pady=(20, 8))
        self.time_label = ctk.CTkLabel(time_card, text="-- min",
                                      font=ctk.CTkFont(size=28, weight="bold"),
                                      text_color=self.PRIMARY_BLUE)
        self.time_label.pack(pady=(0, 20))
        
        # Map Preview Section - Enhanced
        map_section = ctk.CTkFrame(panel, fg_color="transparent")
        map_section.grid(row=2, column=0, sticky="nsew", padx=25, pady=(10, 15))
        map_section.grid_rowconfigure(1, weight=1)
        map_section.grid_columnconfigure(0, weight=1)
        
        map_header = ctk.CTkFrame(map_section, fg_color="transparent")
        map_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(map_header, text="🗺️ Route Map Preview",
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(anchor="w")
        
        # Map container with better aspect ratio
        map_container = ctk.CTkFrame(map_section, fg_color=self.CARD_BG, 
                                    corner_radius=12, border_width=2, border_color=self.BORDER_LIGHT)
        map_container.grid(row=1, column=0, sticky="nsew")
        map_container.grid_rowconfigure(0, weight=1)
        map_container.grid_columnconfigure(0, weight=1)
        
        # Loading overlay
        self.loading_frame = ctk.CTkFrame(map_container, fg_color=self.CARD_BG, corner_radius=12)
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame.grid_rowconfigure(0, weight=1)
        
        loading_content = ctk.CTkFrame(self.loading_frame, fg_color="transparent")
        loading_content.place(relx=0.5, rely=0.5, anchor="center")
        
        self.loading_label = ctk.CTkLabel(loading_content, text="🗺️",
                                         font=ctk.CTkFont(size=50))
        self.loading_label.pack(pady=(0, 15))
        
        self.loading_text = ctk.CTkLabel(loading_content, 
                                        text="Map preview will appear here\nafter calculating route",
                                        font=ctk.CTkFont(size=14),
                                        text_color=self.TEXT_SECONDARY,
                                        justify="center")
        self.loading_text.pack()
        
        # Map label (hidden initially)
        self.map_label = ctk.CTkLabel(map_container, text="", corner_radius=12)
        
        # Directions Section
        directions_section = ctk.CTkFrame(panel, fg_color="transparent")
        directions_section.grid(row=4, column=0, sticky="ew", padx=25, pady=(15, 10))
        ctk.CTkLabel(directions_section, text="🧭 Turn-by-Turn Directions",
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(anchor="w")
        
        self.directions_textbox = ctk.CTkTextbox(
            panel,
            state="disabled",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
            fg_color=self.CARD_BG,
            border_width=2,
            border_color=self.BORDER_LIGHT,
            corner_radius=10,
            height=200
        )
        self.directions_textbox.grid(row=5, column=0, sticky="nsew", padx=25, pady=(5, 25))

    # ---------------------------- STATUS BAR ----------------------------

    def create_status_bar(self):
        status_frame = ctk.CTkFrame(self, fg_color=self.PRIMARY_BLUE, corner_radius=0, height=45)
        status_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="✓ Ready to calculate routes",
            font=ctk.CTkFont(size=13),
            text_color=self.TEXT_LIGHT,
            anchor="w"
        )
        self.status_label.pack(side="left", padx=50, pady=12)

    # ---------------------------- LOADING ANIMATION ----------------------------

    def show_loading(self):
        self.loading_frame.tkraise()
        self.animate_loading()
    
    def animate_loading(self):
        if not self.is_calculating:
            return
        
        emojis = ["🗺️", "🌍", "🧭", "📍"]
        current_text = self.loading_label.cget("text")
        current_index = emojis.index(current_text) if current_text in emojis else 0
        next_index = (current_index + 1) % len(emojis)
        
        self.loading_label.configure(text=emojis[next_index])
        self.after(300, self.animate_loading)
    
    def hide_loading(self):
        self.is_calculating = False
        self.map_label.tkraise()

    # ---------------------------- ROUTE LOGIC ----------------------------

    def start_route_calculation(self):
        if self.is_calculating:
            return
        threading.Thread(target=self.calculate_route, daemon=True).start()

    def calculate_route(self):
        self.is_calculating = True
        self.status_label.configure(text="⏳ Calculating optimal route...")
        self.get_route_button.configure(state="disabled", text="⏳ CALCULATING...", 
                                       fg_color=self.TEXT_SECONDARY)
        
        # Show loading animation
        self.loading_text.configure(text="Calculating route...\nPlease wait")
        self.show_loading()
        
        start_location = self.start_entry.get()
        end_location = self.end_entry.get()
        vehicle = self.vehicle_var.get()

        start_data = self.api_logic.geocode(start_location)
        if start_data["status"] == "error":
            self.is_calculating = False
            self.status_label.configure(text=f"❌ Error: {start_data['message']}")
            self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                          fg_color=self.ACCENT_ORANGE)
            self.loading_text.configure(text="Map preview will appear here\nafter calculating route")
            return
            
        end_data = self.api_logic.geocode(end_location)
        if end_data["status"] == "error":
            self.is_calculating = False
            self.status_label.configure(text=f"❌ Error: {end_data['message']}")
            self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                          fg_color=self.ACCENT_ORANGE)
            self.loading_text.configure(text="Map preview will appear here\nafter calculating route")
            return

        route_data = self.api_logic.get_route(
            {"lat": start_data["lat"], "lng": start_data["lng"]},
            {"lat": end_data["lat"], "lng": end_data["lng"]},
            vehicle
        )
        
        if route_data["status"] == "error":
            self.is_calculating = False
            self.status_label.configure(text=f"❌ Error: {route_data['message']}")
            self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                          fg_color=self.ACCENT_ORANGE)
            self.loading_text.configure(text="Map preview will appear here\nafter calculating route")
            return

        path = route_data["data"]["paths"][0]
        distance_km = path["distance"] / 1000
        time_min = path["time"] / 60000
        instructions = path["instructions"]
        
        # Extract route coordinates for map display
        route_points = None
        if "points" in path and "coordinates" in path["points"]:
            route_points = path["points"]["coordinates"]
        
        directions_text = ""
        for i, inst in enumerate(instructions, 1):
            directions_text += f"{i}. {inst['text']}\n"
        
        self.distance_label.configure(text=f"{distance_km:.2f} km")
        
        if time_min >= 60:
            hours = int(time_min // 60)
            mins = int(time_min % 60)
            self.time_label.configure(text=f"{hours}h {mins}m")
        else:
            self.time_label.configure(text=f"{time_min:.0f} min")
        
        self.directions_textbox.configure(state="normal")
        self.directions_textbox.delete("1.0", "end")
        self.directions_textbox.insert("1.0", directions_text)
        self.directions_textbox.configure(state="disabled")

        # Update map with actual route path
        self.update_map_preview(
            {"lat": start_data["lat"], "lng": start_data["lng"]},
            {"lat": end_data["lat"], "lng": end_data["lng"]},
            route_points
        )

        self.status_label.configure(text=f"✓ Route calculated successfully! Distance: {distance_km:.2f} km • Time: {time_min:.0f} min")
        self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                       fg_color=self.ACCENT_ORANGE)
        
    def update_map_preview(self, start_coords, end_coords, route_points=None):
        url = self.api_logic.get_static_map_url(start_coords, end_coords, route_points, width=1000, height=500)
        if not url:
            self.is_calculating = False
            self.loading_text.configure(text="⚠️ Google Maps API key not configured")
            return
        
        try:
            self.loading_text.configure(text="Loading map...\nPlease wait")
            response = requests.get(url, timeout=15)
            image = Image.open(BytesIO(response.content))
            
            # Get the actual dimensions of the map container
            # Maintain 2:1 aspect ratio for better map visibility
            display_width = 750
            display_height = 375
            
            # Resize with high quality
            image = image.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            self.map_photo = ImageTk.PhotoImage(image)
            self.map_label.configure(image=self.map_photo, text="")
            self.map_label.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
            
            # Hide loading and show map
            self.hide_loading()
            
        except Exception as e:
            self.is_calculating = False
            self.loading_text.configure(text=f"⚠️ Failed to load map preview\n{str(e)}")


# =======================================================================================
# SECTION 3: RUN APP
# =======================================================================================

if __name__ == "__main__":
    api_logic = RouteAPI()
    app = FantasticRouterApp(api_logic)
    app.mainloop()