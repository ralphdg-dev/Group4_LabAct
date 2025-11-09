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
        url = self.route_url + urllib.parse.urlencode({"key": self.key, "vehicle": vehicle}) + op + dp
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

    def get_static_map_url(self, start_coords, end_coords, width=400, height=300):
        """Generate a Google Static Maps URL for the route."""
        if not GOOGLE_MAPS_API_KEY:
            return None
        start = f"{start_coords['lat']},{start_coords['lng']}"
        end = f"{end_coords['lat']},{end_coords['lng']}"
        markers = f"markers=color:blue|label:S|{start}&markers=color:red|label:E|{end}"
        path = f"path=color:0x2596be|weight:4|{start}|{end}"
        url = f"https://maps.googleapis.com/maps/api/staticmap?size={width}x{height}&{markers}&{path}&key={GOOGLE_MAPS_API_KEY}"
        return url

# =======================================================================================
# SECTION 2: GUI APPLICATION
# =======================================================================================

class FantasticRouterApp(ctk.CTk):
    def __init__(self, api_logic):
        super().__init__()
        self.api_logic = api_logic
        self.THEME_COLOR = "#2596be"
        self.ACCENT_COLOR = "#67bed9"
        self.TEXT_COLOR = "#EAF0F6"
        self.BUTTON_COLOR = "#aa534a"
        self.BUTTON_HOVER = "#d5834a"
        self.NEW_BACKGROUND = "#feefce"
        self.SECONDARY_COLOR = "#5a4a78"
        self.HIGHLIGHT_COLOR = "#f0c850"
        self.ERROR_COLOR = "#e74c3c"
        self.WARNING_COLOR = "#f39c12"
        self.SUCCESS_COLOR = "#27ae60"

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Fantastic Tour")
        self.geometry("1000x750")
        self.minsize(900, 650)
        self.configure(fg_color=self.NEW_BACKGROUND)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header_frame()
        self.create_main_content_frame()
        self.create_status_bar()

    # ---------------------------- HEADER FRAME ----------------------------

    def create_header_frame(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.THEME_COLOR, corner_radius=0, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_rowconfigure(0, weight=1)

        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent", width=80)
        logo_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        try:
            logo_image = ctk.CTkImage(Image.open("f4_logo.png"), size=(60, 60))
            logo_label = ctk.CTkLabel(logo_frame, image=logo_image, text="", fg_color=self.ACCENT_COLOR, corner_radius=10)
            logo_label.pack(padx=5, pady=5)
        except FileNotFoundError:
            logo_placeholder = ctk.CTkFrame(logo_frame, width=60, height=60, fg_color=self.SECONDARY_COLOR, corner_radius=10,
                                            border_color=self.HIGHLIGHT_COLOR, border_width=2)
            logo_placeholder.pack(padx=5, pady=5)
            logo_text = ctk.CTkLabel(logo_placeholder, text="F4", font=ctk.CTkFont(family="Impact", size=20, weight="bold"),
                                     text_color=self.TEXT_COLOR)
            logo_text.place(relx=0.5, rely=0.5, anchor="center")
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w", padx=0, pady=10)
        title_label = ctk.CTkLabel(title_frame, text="FANTASTIC TOUR",
                                   font=ctk.CTkFont(family="Impact", size=32, weight="bold"),
                                   text_color=self.TEXT_COLOR)
        title_label.pack(side="left")

    # ---------------------------- MAIN CONTENT ----------------------------

    def create_main_content_frame(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_rowconfigure(0, weight=1)

        self.create_input_frame(main_frame)
        self.create_output_frame(main_frame)

    def create_input_frame(self, parent):
        input_frame = ctk.CTkFrame(parent, fg_color=self.THEME_COLOR, corner_radius=15,
                                 border_color=self.ACCENT_COLOR, border_width=2)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)

        input_header = ctk.CTkFrame(input_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10, height=40)
        input_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        ctk.CTkLabel(input_header, text="MISSION PARAMETERS", font=ctk.CTkFont(weight="bold", size=16),
                     text_color=self.TEXT_COLOR).grid(row=0, column=0, padx=10, pady=5)

        location_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        location_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        origin_header = ctk.CTkFrame(location_frame, fg_color="transparent")
        origin_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(origin_header, text="🏢", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(origin_header, text="The Baxter Building", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.start_entry = ctk.CTkEntry(location_frame, placeholder_text="e.g., Times Square, NY",
                                      border_color=self.ACCENT_COLOR, border_width=1, height=35)
        self.start_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        dest_header = ctk.CTkFrame(location_frame, fg_color="transparent")
        dest_header.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(dest_header, text="🏰", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(dest_header, text="Latveria", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.end_entry = ctk.CTkEntry(location_frame, placeholder_text="e.g., Eiffel Tower, Paris",
                                    border_color=self.ACCENT_COLOR, border_width=1, height=35)
        self.end_entry.grid(row=3, column=0, sticky="ew", pady=(0, 20))

        vehicle_frame = ctk.CTkFrame(input_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10)
        vehicle_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=10)
        vehicle_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(vehicle_frame, text="⚡ MODE OF TRANSPORTATION", font=ctk.CTkFont(weight="bold"),
                     text_color=self.TEXT_COLOR).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        self.vehicle_var = tkinter.StringVar(value="car")
        vehicles = [("🚗 Fantasticar", "car", ""), ("🚲 Bike", "bike", ""), ("👣 Foot", "foot", "")]
        for i, (text, value, desc) in enumerate(vehicles, 1):
            vehicle_option = ctk.CTkFrame(vehicle_frame, fg_color="transparent")
            vehicle_option.grid(row=i, column=0, sticky="ew", padx=10, pady=2)
            rb = ctk.CTkRadioButton(vehicle_option, text=text, variable=self.vehicle_var, value=value,
                                     fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER,
                                     font=ctk.CTkFont(weight="bold"))
            rb.pack(side="left")
            desc_label = ctk.CTkLabel(vehicle_option, text=desc, font=ctk.CTkFont(size=11),
                                      text_color=self.TEXT_COLOR)
            desc_label.pack(side="left", padx=(5, 0))

        button_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=20)
        self.get_route_button = ctk.CTkButton(button_frame, text="IT'S CLOBBERIN' TIME!",
                                              font=ctk.CTkFont(size=18, weight="bold", family="Impact"),
                                              fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER,
                                              border_color=self.HIGHLIGHT_COLOR, border_width=2, height=50,
                                              corner_radius=25, command=self.start_route_calculation)
        self.get_route_button.pack(fill="x", pady=10)

    # ---------------------------- OUTPUT FRAME ----------------------------

    def create_output_frame(self, parent):
        output_frame = ctk.CTkFrame(parent, fg_color=self.THEME_COLOR, corner_radius=15,
                                  border_color=self.ACCENT_COLOR, border_width=2)
        output_frame.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        output_frame.grid_rowconfigure(1, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)

        output_header = ctk.CTkFrame(output_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10, height=40)
        output_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        ctk.CTkLabel(output_header, text="MISSION BRIEFING", font=ctk.CTkFont(weight="bold", size=16),
                     text_color=self.TEXT_COLOR).pack(pady=5)

        summary_frame = ctk.CTkFrame(output_frame, fg_color=self.ACCENT_COLOR, corner_radius=10)
        summary_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        summary_frame.grid_columnconfigure((0, 1), weight=1)
        distance_container = ctk.CTkFrame(summary_frame, fg_color=self.THEME_COLOR, corner_radius=8)
        distance_container.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(distance_container, text="📏 DISTANCE", font=ctk.CTkFont(weight="bold", size=12),
                    text_color=self.TEXT_COLOR).pack(pady=(5, 0))
        self.distance_label = ctk.CTkLabel(distance_container, text="--",
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=self.HIGHLIGHT_COLOR)
        self.distance_label.pack(pady=(0, 5))

        time_container = ctk.CTkFrame(summary_frame, fg_color=self.THEME_COLOR, corner_radius=8)
        time_container.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(time_container, text="⏱️ TIME", font=ctk.CTkFont(weight="bold", size=12),
                    text_color=self.TEXT_COLOR).pack(pady=(5, 0))
        self.time_label = ctk.CTkLabel(time_container, text="--",
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     text_color=self.HIGHLIGHT_COLOR)
        self.time_label.pack(pady=(0, 5))

        directions_header = ctk.CTkFrame(output_frame, fg_color="transparent")
        directions_header.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 0))
        ctk.CTkLabel(directions_header, text="🗺️ TURN-BY-TURN DIRECTIONS",
                    font=ctk.CTkFont(weight="bold"),
                    text_color=self.TEXT_COLOR).pack(side="left")

        self.directions_textbox = ctk.CTkTextbox(output_frame, state="disabled",
                                                font=ctk.CTkFont(family="Consolas", size=12),
                                                wrap="word",
                                                border_color=self.ACCENT_COLOR, border_width=2,
                                                corner_radius=10)
        self.directions_textbox.grid(row=3, column=0, sticky="nsew", padx=15, pady=(5, 15))

        self.map_label = ctk.CTkLabel(output_frame, text="Map Preview will appear here", fg_color=self.THEME_COLOR,
                                     text_color=self.TEXT_COLOR, corner_radius=10, height=250)
        self.map_label.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 15))

    # ---------------------------- STATUS BAR ----------------------------

    def create_status_bar(self):
        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12), anchor="w",
                                        fg_color=self.THEME_COLOR, text_color=self.TEXT_COLOR)
        self.status_label.grid(row=2, column=0, sticky="ew")

    # ---------------------------- ROUTE LOGIC ----------------------------

    def start_route_calculation(self):
        threading.Thread(target=self.calculate_route, daemon=True).start()

    def calculate_route(self):
        self.status_label.configure(text="🛠️ Calculating route...")
        self.get_route_button.configure(state="disabled")
        start_location = self.start_entry.get()
        end_location = self.end_entry.get()
        vehicle = self.vehicle_var.get()

        start_data = self.api_logic.geocode(start_location)
        if start_data["status"] == "error":
            self.status_label.configure(text=f"❌ {start_data['message']}")
            self.get_route_button.configure(state="normal")
            return
        end_data = self.api_logic.geocode(end_location)
        if end_data["status"] == "error":
            self.status_label.configure(text=f"❌ {end_data['message']}")
            self.get_route_button.configure(state="normal")
            return

        route_data = self.api_logic.get_route({"lat": start_data["lat"], "lng": start_data["lng"]},
                                             {"lat": end_data["lat"], "lng": end_data["lng"]},
                                             vehicle)
        if route_data["status"] == "error":
            self.status_label.configure(text=f"❌ {route_data['message']}")
            self.get_route_button.configure(state="normal")
            return

        path = route_data["data"]["paths"][0]
        distance_km = path["distance"] / 1000
        time_min = path["time"] / 60000
        instructions = path["instructions"]
        directions_text = "\n".join([f"{i+1}. {inst['text']}" for i, inst in enumerate(instructions)])

        self.distance_label.configure(text=f"{distance_km:.2f} km")
        self.time_label.configure(text=f"{time_min:.1f} min")
        self.directions_textbox.configure(state="normal")
        self.directions_textbox.delete("1.0", "end")
        self.directions_textbox.insert("1.0", directions_text)
        self.directions_textbox.configure(state="disabled")

        self.update_map_preview({"lat": start_data["lat"], "lng": start_data["lng"]},
                                {"lat": end_data["lat"], "lng": end_data["lng"]})

        self.status_label.configure(text="✅ Route calculation complete!")
        self.get_route_button.configure(state="normal")
        
    def update_map_preview(self, start_coords, end_coords):
        url = self.api_logic.get_static_map_url(start_coords, end_coords)
        if not url:
            self.map_label.configure(text="Google Maps API key not found")
            return
        try:
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))
            # Use the new resampling enum instead of the removed ANTIALIAS
            image = image.resize((600, 250), Image.Resampling.LANCZOS)
            self.map_photo = ImageTk.PhotoImage(image)
            self.map_label.configure(image=self.map_photo, text="")
        except Exception as e:
            self.map_label.configure(text=f"Failed to load map: {str(e)}")


# =======================================================================================
# SECTION 3: RUN APP
# =======================================================================================

if __name__ == "__main__":
    api_logic = RouteAPI()
    app = FantasticRouterApp(api_logic)
    app.mainloop()
