import os
from dotenv import load_dotenv
import customtkinter as ctk
import tkinter
import requests
import urllib.parse
import threading
from tkinter import messagebox
import webbrowser

try:
    import tkintermapview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False
    print("Note: Install tkintermapview for embedded maps: pip install tkintermapview")

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

    def get_google_maps_url(self, start_coords, end_coords, vehicle):
        """Generate a Google Maps URL for interactive viewing in browser."""
        start = f"{start_coords['lat']},{start_coords['lng']}"
        end = f"{end_coords['lat']},{end_coords['lng']}"
        
        travel_mode_map = {
            'car': 'driving',
            'bike': 'bicycling',
            'foot': 'walking'
        }
        mode = travel_mode_map.get(vehicle, 'driving')
        
        url = f"https://www.google.com/maps/dir/?api=1&origin={start}&destination={end}&travelmode={mode}"
        return url

class FantasticRouterApp(ctk.CTk):
    def __init__(self, api_logic):
        super().__init__()
        self.api_logic = api_logic
        self.is_calculating = False
        self.current_route_data = None
        self.map_markers = []
        self.map_path = None 
        
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
        self.geometry("1400x900")
        self.minsize(1200, 750)
        self.configure(fg_color=self.BG_GRADIENT_START)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header_frame()
        self.create_main_content_frame()
        self.create_status_bar()

    def create_header_frame(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.PRIMARY_BLUE, corner_radius=0, height=110)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(0, weight=1)
        
        content_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=50, pady=25)
        
        left_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_section.pack(side="left", fill="y")
        
        try:
            from PIL import Image
            logo_image = ctk.CTkImage(Image.open("f4_logo.png"), size=(55, 55))
            logo_label = ctk.CTkLabel(left_section, image=logo_image, text="")
            logo_label.pack(side="left", padx=(0, 20))
        except:
            logo_frame = ctk.CTkFrame(left_section, width=55, height=55, 
                                     fg_color=self.DARK_BLUE, corner_radius=27)
            logo_frame.pack(side="left", padx=(0, 20))
            logo_frame.pack_propagate(False)
            ctk.CTkLabel(logo_frame, text="F4", font=ctk.CTkFont(size=22, weight="bold"),
                        text_color=self.TEXT_LIGHT).place(relx=0.5, rely=0.5, anchor="center")
        
        title_section = ctk.CTkFrame(left_section, fg_color="transparent")
        title_section.pack(side="left")
        ctk.CTkLabel(title_section, text="FANTASTIC TOUR",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(anchor="w")
        ctk.CTkLabel(title_section, text="Advanced Route Planning & Navigation System",
                    font=ctk.CTkFont(size=14),
                    text_color=self.LIGHT_BLUE).pack(anchor="w", pady=(2, 0))

    def create_main_content_frame(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=35, pady=25)
        main_frame.grid_columnconfigure(0, weight=2, minsize=450)
        main_frame.grid_columnconfigure(1, weight=3, minsize=800)
        main_frame.grid_rowconfigure(0, weight=1)

        self.create_input_panel(main_frame)
        self.create_output_panel(main_frame)

    def create_input_panel(self, parent):
        panel_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        panel_container.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        panel = ctk.CTkFrame(panel_container, fg_color=self.BG_WHITE, corner_radius=15, 
                            border_width=0)
        panel.pack(fill="both", expand=True)
        panel.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkFrame(panel, fg_color=self.PRIMARY_BLUE, corner_radius=12, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(25, 20))
        ctk.CTkLabel(header, text="🎯 Route Configuration", 
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(pady=15)
        
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
        
        ctk.CTkFrame(vehicle_frame, fg_color="transparent", height=10).pack()
        
        button_container = ctk.CTkFrame(panel, fg_color="transparent")
        button_container.grid(row=4, column=0, sticky="ew", padx=25, pady=(25, 20))
        
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
        
        links_btn = ctk.CTkButton(
            button_container,
            text="🌐 Open in Google Maps",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.PRIMARY_BLUE,
            hover_color=self.DARK_BLUE,
            height=45,
            corner_radius=10,
            command=self.open_google_maps
        )
        links_btn.pack(fill="x", pady=(15, 0))
        self.view_gmaps_btn = links_btn
        self.view_gmaps_btn.configure(state="disabled")


    def create_output_panel(self, parent):
        scroll_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_container.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        scroll_container.grid_columnconfigure(0, weight=1)
        scroll_container.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkFrame(scroll_container, fg_color=self.BG_WHITE, corner_radius=15)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=6)
        panel.grid_rowconfigure(5, weight=2)
        panel.grid_rowconfigure(6, weight=1)
        header = ctk.CTkFrame(panel, fg_color=self.PRIMARY_BLUE, corner_radius=12, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(25, 20))
        ctk.CTkLabel(header, text="📊 Route Information & Map", 
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color=self.TEXT_LIGHT).pack(pady=15)

        summary_container = ctk.CTkFrame(panel, fg_color="transparent")
        summary_container.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 20))
        summary_container.grid_columnconfigure((0, 1), weight=1)

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

        map_header_section = ctk.CTkFrame(panel, fg_color="transparent")
        map_header_section.grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 10))
        ctk.CTkLabel(map_header_section, text="🗺️ Interactive Map View (Expanded)",
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=self.TEXT_DARK).pack(anchor="w")

        map_height = 500

        if MAP_AVAILABLE:
            map_frame = ctk.CTkFrame(
                panel,
                fg_color=self.CARD_BG,
                corner_radius=10,
                border_width=2,
                border_color=self.BORDER_LIGHT,
                height=map_height
            )
            map_frame.grid(row=3, column=0, sticky="ew", padx=25, pady=(10, 20))
            map_frame.grid_propagate(False)

            self.map_widget = tkintermapview.TkinterMapView(map_frame, corner_radius=8)
            self.map_widget.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.97, relheight=0.97)
            self.map_widget.set_position(14.5995, 120.9842)
            self.map_widget.set_zoom(12)
        else:
            map_placeholder = ctk.CTkFrame(
                panel,
                fg_color=self.CARD_BG,
                corner_radius=10,
                border_width=2,
                border_color=self.BORDER_LIGHT,
                height=map_height
            )
            map_placeholder.grid(row=3, column=0, sticky="ew", padx=25, pady=(10, 20))
            map_placeholder.grid_propagate(False)
            ctk.CTkLabel(
                map_placeholder,
                text="📦 Map Widget Not Available\n\nInstall tkintermapview:\npip install tkintermapview",
                font=ctk.CTkFont(size=15),
                text_color=self.TEXT_SECONDARY,
                justify="center"
            ).place(relx=0.5, rely=0.5, anchor="center")

        directions_section = ctk.CTkFrame(panel, fg_color="transparent")
        directions_section.grid(row=4, column=0, sticky="ew", padx=25, pady=(10, 10))
        ctk.CTkLabel(
            directions_section,
            text="🧭 Turn-by-Turn Directions",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.TEXT_DARK
        ).pack(anchor="w")

        self.directions_textbox = ctk.CTkTextbox(
            panel,
            state="disabled",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
            fg_color=self.CARD_BG,
            border_width=2,
            border_color=self.BORDER_LIGHT,
            corner_radius=10,
            height=map_height
        )
        self.directions_textbox.grid(row=5, column=0, sticky="ew", padx=25, pady=(5, 20))

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

    def clear_map(self):
        """Clear all markers and paths from the map."""
        if not MAP_AVAILABLE:
            return
        
        for marker in self.map_markers:
            try:
                marker.delete()
            except:
                pass
        self.map_markers.clear()
        
        if self.map_path:
            try:
                self.map_path.delete()
            except:
                pass
            self.map_path = None

    def update_map(self, start_coords, end_coords, route_points=None):
        """Update the embedded map with route information."""
        if not MAP_AVAILABLE:
            return
        
        self.clear_map()
        
        start_marker = self.map_widget.set_marker(
            start_coords['lat'], 
            start_coords['lng'],
            text="Start",
            marker_color_circle="green",
            marker_color_outside="darkgreen"
        )
        self.map_markers.append(start_marker)
        
        end_marker = self.map_widget.set_marker(
            end_coords['lat'], 
            end_coords['lng'],
            text="Destination",
            marker_color_circle="red",
            marker_color_outside="darkred"
        )
        self.map_markers.append(end_marker)
        
        if route_points and len(route_points) > 1:
            path_coords = [(pt[1], pt[0]) for pt in route_points] 
            
            self.map_path = self.map_widget.set_path(path_coords, color="#2196F3", width=4)
        
        try:
            top_left = (
                max(start_coords['lat'], end_coords['lat']), 
                min(start_coords['lng'], end_coords['lng'])  
            )
            bottom_right = (
                min(start_coords['lat'], end_coords['lat']),  
                max(start_coords['lng'], end_coords['lng'])   
            )
            self.map_widget.fit_bounding_box(top_left, bottom_right)
        except Exception as e:
            print(f"[Map Warning] Could not fit bounding box: {e}")
            center_lat = (start_coords['lat'] + end_coords['lat']) / 2
            center_lng = (start_coords['lng'] + end_coords['lng']) / 2
            self.map_widget.set_position(center_lat, center_lng)
            self.map_widget.set_zoom(10)

    def start_route_calculation(self):
        if self.is_calculating:
            return
        threading.Thread(target=self.calculate_route, daemon=True).start()

    def calculate_route(self):
        self.is_calculating = True
        self.status_label.configure(text="⏳ Calculating optimal route...")
        self.get_route_button.configure(state="disabled", text="⏳ CALCULATING...", 
                                       fg_color=self.TEXT_SECONDARY)
        
        start_location = self.start_entry.get()
        end_location = self.end_entry.get()
        vehicle = self.vehicle_var.get()

        start_data = self.api_logic.geocode(start_location)
        if start_data["status"] == "error":
            self.is_calculating = False
            self.status_label.configure(text=f"❌ Error: {start_data['message']}")
            self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                          fg_color=self.ACCENT_ORANGE)
            return
            
        end_data = self.api_logic.geocode(end_location)
        if end_data["status"] == "error":
            self.is_calculating = False
            self.status_label.configure(text=f"❌ Error: {end_data['message']}")
            self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                          fg_color=self.ACCENT_ORANGE)
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
            return

        path = route_data["data"]["paths"][0]
        distance_km = path["distance"] / 1000
        time_min = path["time"] / 60000
        instructions = path["instructions"]
        
        route_points = None
        if "points" in path and "coordinates" in path["points"]:
            route_points = path["points"]["coordinates"]
        
        self.current_route_data = {
            "start_coords": {"lat": start_data["lat"], "lng": start_data["lng"]},
            "end_coords": {"lat": end_data["lat"], "lng": end_data["lng"]},
            "route_points": route_points,
            "vehicle": vehicle
        }
        
        if MAP_AVAILABLE:
            self.after(0, lambda: self.update_map(
                self.current_route_data["start_coords"],
                self.current_route_data["end_coords"],
                route_points
            ))
        
        self.distance_label.configure(text=f"{distance_km:.2f} km")
        
        if time_min >= 60:
            hours = int(time_min // 60)
            mins = int(time_min % 60)
            self.time_label.configure(text=f"{hours}h {mins}m")
        else:
            self.time_label.configure(text=f"{time_min:.0f} min")
        
        directions_text = ""
        for i, inst in enumerate(instructions, 1):
            directions_text += f"{i}. {inst['text']}\n"
        
        self.directions_textbox.configure(state="normal")
        self.directions_textbox.delete("1.0", "end")
        self.directions_textbox.insert("1.0", directions_text)
        self.directions_textbox.configure(state="disabled")

        self.view_gmaps_btn.configure(state="normal")

        self.status_label.configure(text=f"✓ Route calculated! Distance: {distance_km:.2f} km • Time: {time_min:.0f} min")
        self.get_route_button.configure(state="normal", text="🚀 CALCULATE ROUTE",
                                       fg_color=self.ACCENT_ORANGE)
        self.is_calculating = False
    
    def open_google_maps(self):
        """Open route in Google Maps."""
        if not self.current_route_data:
            messagebox.showwarning("No Route", "Please calculate a route first.")
            return
        
        try:
            url = self.api_logic.get_google_maps_url(
                self.current_route_data["start_coords"],
                self.current_route_data["end_coords"],
                self.current_route_data["vehicle"]
            )
            webbrowser.open(url)
            self.status_label.configure(text="✓ Route opened in Google Maps!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Google Maps: {str(e)}")

if __name__ == "__main__":
    api_logic = RouteAPI()
    app = FantasticRouterApp(api_logic)
    app.mainloop()