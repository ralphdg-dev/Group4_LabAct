import os
from dotenv import load_dotenv
import customtkinter as ctk
import tkinter
import requests
import urllib.parse
import threading
from PIL import Image, ImageTk
# =======================================================================================
# SECTION 1: API LOGIC
# This class contains the original, non-GUI logic for interacting with the API.
# We've removed the print statements to let the GUI handle all user interaction.
# =======================================================================================

load_dotenv()
GRAPHOPPER_API_KEY = os.getenv("GRAPHHOPPER_API_KEY")

class RouteAPI:
    def __init__(self):
        self.route_url = "https://graphhopper.com/api/1/route?"
        self.geocode_url = "https://graphhopper.com/api/1/geocode?"
        self.key = GRAPHOPPER_API_KEY
    
    def geocode(self, location):
        """Geocodes a location string to get its latitude and longitude."""
        if not location or not location.strip():
            return {"status": "error", "message": "Location cannot be empty."}

        url = self.geocode_url + urllib.parse.urlencode({
            "q": location,
            "limit": "1",
            "key": self.key
        })
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if response.status_code == 200 and data.get("hits"):
                point = data["hits"][0]["point"]
                name = data["hits"][0].get("name", "Unknown")
                country = data["hits"][0].get("country", "")
                state = data["hits"][0].get("state", "")
                full_name = f"{name}, {state}, {country}".strip(", ")
                return {"status": "success", "lat": point["lat"], "lng": point["lng"], "name": full_name}
            else:
                return {"status": "error", "message": data.get("message", f"No results for {location}")}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Network error: {e}"}

    def get_route(self, start_coords, end_coords, vehicle):
        """Fetches the route between two points for a given vehicle."""
        op = f"&point={start_coords['lat']},{start_coords['lng']}"
        dp = f"&point={end_coords['lat']},{end_coords['lng']}"
        
        url = self.route_url + urllib.parse.urlencode({"key": self.key, "vehicle": vehicle}) + op + dp
        try:
            response = requests.get(url, timeout=15)
            data = response.json()
            if response.status_code == 200:
                return {"status": "success", "data": data}
            else:
                return {"status": "error", "message": data.get("message", "Routing API error")}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Network error: {e}"}

# =======================================================================================
# SECTION 2: GUI APPLICATION
# This class builds and manages the entire user interface using customtkinter.
# =======================================================================================
class FantasticRouterApp(ctk.CTk):
    def __init__(self, api_logic):
        super().__init__()
        self.api_logic = api_logic

        # --- Fantastic Four Color Palette ---
        self.THEME_COLOR = "#2596be"  # Mr. Fantastic Blue
        self.ACCENT_COLOR = "#67bed9"  # Cosmic Blue
        self.TEXT_COLOR = "#EAF0F6"
        self.BUTTON_COLOR = "#aa534a"  # Human Torch Orange
        self.BUTTON_HOVER = "#d5834a"
        self.NEW_BACKGROUND = "#feefce"  # Cream background
        self.SECONDARY_COLOR = "#5a4a78"  # Purple for accents
        self.HIGHLIGHT_COLOR = "#f0c850"  # Yellow for highlights

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Fantastic Tour")
        self.geometry("1000x750")
        self.minsize(900, 650)
        self.configure(fg_color=self.NEW_BACKGROUND)

        # --- Configure Main Grid Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Initialize UI Components ---
        self.create_header_frame()
        self.create_main_content_frame()
        self.create_status_bar()

    def create_header_frame(self):
        """Creates the top banner with the logo and title."""
        header_frame = ctk.CTkFrame(self, fg_color=self.THEME_COLOR, corner_radius=0, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_rowconfigure(0, weight=1)

        # Logo with enhanced styling
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent", width=80)
        logo_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        try:
            logo_image = ctk.CTkImage(Image.open("f4_logo.png"), size=(60, 60))
            logo_label = ctk.CTkLabel(logo_frame, image=logo_image, text="", 
                                     fg_color=self.ACCENT_COLOR, corner_radius=10)
            logo_label.pack(padx=5, pady=5)
        except FileNotFoundError:
            # Fallback logo placeholder with F4 styling
            logo_placeholder = ctk.CTkFrame(logo_frame, width=60, height=60, 
                                          fg_color=self.SECONDARY_COLOR, corner_radius=10,
                                          border_color=self.HIGHLIGHT_COLOR, border_width=2)
            logo_placeholder.pack(padx=5, pady=5)
            logo_text = ctk.CTkLabel(logo_placeholder, text="F4", 
                                   font=ctk.CTkFont(family="Impact", size=20, weight="bold"),
                                   text_color=self.TEXT_COLOR)
            logo_text.place(relx=0.5, rely=0.5, anchor="center")

        # Enhanced title with comic book styling
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w", padx=0, pady=10)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="FANTASTIC TOUR",
            font=ctk.CTkFont(family="Impact", size=32, weight="bold"),
            text_color=self.TEXT_COLOR
        )
        title_label.pack(side="left")
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=self.HIGHLIGHT_COLOR
        )
        subtitle_label.pack(side="left", padx=(10, 0), pady=(8, 0))

    def create_main_content_frame(self):
        """Creates the main area with input fields and the results display."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_rowconfigure(0, weight=1)

        self.create_input_frame(main_frame)
        self.create_output_frame(main_frame)
        
    def create_input_frame(self, parent):
        """Creates the left-side panel for user inputs with enhanced Fantastic Four styling."""
        input_frame = ctk.CTkFrame(parent, fg_color=self.THEME_COLOR, corner_radius=15,
                                 border_color=self.ACCENT_COLOR, border_width=2)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Header for input section
        input_header = ctk.CTkFrame(input_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10, height=40)
        input_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        input_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(input_header, text="MISSION PARAMETERS", 
                    font=ctk.CTkFont(weight="bold", size=16),
                    text_color=self.TEXT_COLOR).grid(row=0, column=0, padx=10, pady=5)
        
        # --- Location Inputs with enhanced styling ---
        location_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        location_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        
        # Origin input with icon
        origin_header = ctk.CTkFrame(location_frame, fg_color="transparent")
        origin_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(origin_header, text="🏢", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(origin_header, text="The Baxter Building", 
                    font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.start_entry = ctk.CTkEntry(location_frame, placeholder_text="e.g., Times Square, NY",
                                      border_color=self.ACCENT_COLOR, border_width=1,
                                      height=35)
        self.start_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # Destination input with icon
        dest_header = ctk.CTkFrame(location_frame, fg_color="transparent")
        dest_header.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(dest_header, text="🏰", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(dest_header, text="Latveria", 
                    font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.end_entry = ctk.CTkEntry(location_frame, placeholder_text="e.g., Eiffel Tower, Paris",
                                    border_color=self.ACCENT_COLOR, border_width=1,
                                    height=35)
        self.end_entry.grid(row=3, column=0, sticky="ew", pady=(0, 20))

        # --- Vehicle Selection with enhanced styling ---
        vehicle_frame = ctk.CTkFrame(input_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10)
        vehicle_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=10)
        vehicle_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(vehicle_frame, text="⚡ MODE OF TRANSPORTATION", 
                    font=ctk.CTkFont(weight="bold"),
                    text_color=self.TEXT_COLOR).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        self.vehicle_var = tkinter.StringVar(value="car")
        
        vehicles = [
            ("🚗 Fantasticar", "car", ""),
            ("🚲 Bike", "bike", ""),
            ("👣 Foot", "foot", "")
        ]
        
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

        # --- Unit Selection ---
        unit_frame = ctk.CTkFrame(input_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10)
        unit_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=10)
        
        ctk.CTkLabel(unit_frame, text="📏 MEASUREMENT SYSTEM", 
                    font=ctk.CTkFont(weight="bold"),
                    text_color=self.TEXT_COLOR).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        self.unit_var = tkinter.StringVar(value="metric")
        
        unit_option_frame = ctk.CTkFrame(unit_frame, fg_color="transparent")
        unit_option_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        metric_rb = ctk.CTkRadioButton(unit_option_frame, text="Metric (km)", variable=self.unit_var, value="metric",
                                     fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER)
        metric_rb.pack(side="left", padx=(0, 15))
        
        imperial_rb = ctk.CTkRadioButton(unit_option_frame, text="Imperial (miles)", variable=self.unit_var, value="imperial",
                                       fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER)
        imperial_rb.pack(side="left")

        # --- Action Button with enhanced styling ---
        button_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=20)
        
        self.get_route_button = ctk.CTkButton(
            button_frame, 
            text="IT'S CLOBBERIN' TIME!",
            font=ctk.CTkFont(size=18, weight="bold", family="Impact"),
            fg_color=self.BUTTON_COLOR,
            hover_color=self.BUTTON_HOVER,
            border_color=self.HIGHLIGHT_COLOR,
            border_width=2,
            height=50,
            corner_radius=25,
            command=self.start_route_calculation
        )
        self.get_route_button.pack(fill="x", pady=10)

    def create_output_frame(self, parent):
        """Creates the right-side panel for displaying results with enhanced styling."""
        output_frame = ctk.CTkFrame(parent, fg_color=self.THEME_COLOR, corner_radius=15,
                                  border_color=self.ACCENT_COLOR, border_width=2)
        output_frame.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        output_frame.grid_rowconfigure(1, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)

        # Output header
        output_header = ctk.CTkFrame(output_frame, fg_color=self.SECONDARY_COLOR, corner_radius=10, height=40)
        output_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        ctk.CTkLabel(output_header, text="MISSION BRIEFING", 
                    font=ctk.CTkFont(weight="bold", size=16),
                    text_color=self.TEXT_COLOR).pack(pady=5)

        # --- Summary Frame with comic book style ---
        summary_frame = ctk.CTkFrame(output_frame, fg_color=self.ACCENT_COLOR, corner_radius=10)
        summary_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        summary_frame.grid_columnconfigure((0, 1), weight=1)

        # Distance display
        distance_container = ctk.CTkFrame(summary_frame, fg_color=self.THEME_COLOR, corner_radius=8)
        distance_container.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(distance_container, text="📏 DISTANCE", font=ctk.CTkFont(weight="bold", size=12),
                    text_color=self.TEXT_COLOR).pack(pady=(5, 0))
        self.distance_label = ctk.CTkLabel(distance_container, text="--", 
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=self.HIGHLIGHT_COLOR)
        self.distance_label.pack(pady=(0, 5))

        # Time display
        time_container = ctk.CTkFrame(summary_frame, fg_color=self.THEME_COLOR, corner_radius=8)
        time_container.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(time_container, text="⏱️ TIME", font=ctk.CTkFont(weight="bold", size=12),
                    text_color=self.TEXT_COLOR).pack(pady=(5, 0))
        self.time_label = ctk.CTkLabel(time_container, text="--", 
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     text_color=self.HIGHLIGHT_COLOR)
        self.time_label.pack(pady=(0, 5))

        # --- Directions Textbox with enhanced styling ---
        directions_header = ctk.CTkFrame(output_frame, fg_color="transparent")
        directions_header.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 0))
        ctk.CTkLabel(directions_header, text="🗺️ TURN-BY-TURN DIRECTIONS", 
                    font=ctk.CTkFont(weight="bold"),
                    text_color=self.TEXT_COLOR).pack(side="left")
        
        self.directions_textbox = ctk.CTkTextbox(
            output_frame, 
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            border_color=self.ACCENT_COLOR,
            border_width=2,
            corner_radius=10,
            fg_color="#1a1a2e",
            text_color="#ffffff"
        )
        self.directions_textbox.grid(row=3, column=0, sticky="nsew", padx=15, pady=(5, 15))
        
    def create_status_bar(self):
        """Creates a status bar at the bottom of the window."""
        status_frame = ctk.CTkFrame(self, fg_color=self.SECONDARY_COLOR, corner_radius=0, height=30)
        status_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame, 
            text="  Ready for mission planning...", 
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_COLOR,
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=15)
        
        # Version info
        version_label = ctk.CTkLabel(
            status_frame,
            text="Fantastic Tour v1.0  ",
            font=ctk.CTkFont(size=10),
            text_color=self.HIGHLIGHT_COLOR
        )
        version_label.grid(row=0, column=1, sticky="e", padx=15)

    def start_route_calculation(self):
        """Disables the button and starts the API calls in a new thread to prevent GUI freezing."""
        self.get_route_button.configure(state="disabled", text="RECALIBRATING...")
        # Create and start a new thread
        thread = threading.Thread(target=self.get_route_logic)
        thread.daemon = True # Allows main program to exit even if thread is running
        thread.start()

    def get_route_logic(self):
        """The core logic that runs in the background thread."""
        start_loc = self.start_entry.get()
        dest_loc = self.end_entry.get()
        vehicle = self.vehicle_var.get()

        # --- Geocode Origin ---
        self.update_status("🔍 Analyzing origin coordinates...", "blue")
        orig = self.api_logic.geocode(start_loc)
        if orig['status'] == 'error':
            self.update_status(f"❌ Origin Error: {orig['message']}", "red")
            self.reset_button()
            return

        # --- Geocode Destination ---
        self.update_status(f"📍 Found {orig['name']}. Analyzing destination...", "blue")
        dest = self.api_logic.geocode(dest_loc)
        if dest['status'] == 'error':
            self.update_status(f"❌ Destination Error: {dest['message']}", "red")
            self.reset_button()
            return
        
        if orig['lat'] == dest['lat'] and orig['lng'] == dest['lng']:
            self.update_status("🔥 Flame Off! Origin and destination are the same.", "orange")
            self.reset_button()
            return

        # --- Get Route ---
        self.update_status(f"🎯 Found {dest['name']}. Plotting course... Flame On! 🔥", "blue")
        route_info = self.api_logic.get_route(orig, dest, vehicle)
        if route_info['status'] == 'error':
            self.update_status(f"❌ Routing Error: {route_info['message']}", "red")
            self.reset_button()
            return

        # --- Process and Display Results ---
        self.update_status("✅ Route calculated! Assembling report...", "green")
        self.after(100, lambda: self.display_results(route_info['data'])) # Safely update GUI from main thread
        
    def display_results(self, data):
        """Formats the API data and updates the GUI components."""
        path = data['paths'][0]
        
        # Format Summary
        distance = self.format_distance(path['distance'])
        time = self.format_time(path['time'])
        self.distance_label.configure(text=f"{distance}")
        self.time_label.configure(text=f"{time}")
        
        # Format Directions
        directions_text = "🚀 FANTASTIC TOUR MISSION BRIEFING 🚀\n" + "="*50 + "\n\n"
        for i, instruction in enumerate(path['instructions'], 1):
            dist = self.format_distance(instruction['distance'])
            text = instruction['text']
            # Enhanced icons for better visual representation
            if "arrived" in text.lower():
                icon = "🏁 ARRIVED"
            elif "turn left" in text.lower():
                icon = "↩️ LEFT"
            elif "turn right" in text.lower():
                icon = "↪️ RIGHT"
            elif "roundabout" in text.lower():
                icon = "🔄 ROUND"
            elif "keep" in text.lower():
                icon = "⬆️ CONTINUE"
            elif "exit" in text.lower():
                icon = "🚪 EXIT"
            else:
                icon = "➡️ NEXT"
                
            directions_text += f"{i:>2}. {icon:<12} {text:<40} [{dist}]\n"
        
        directions_text += f"\n{'='*50}\n✨ MISSION ACCOMPLISHED! ✨"
        
        self.directions_textbox.configure(state="normal")
        self.directions_textbox.delete("1.0", "end")
        self.directions_textbox.insert("1.0", directions_text)
        self.directions_textbox.configure(state="disabled")

        self.reset_button()
        self.update_status("🎉 Mission accomplished! Route briefing ready.", "green")
        
    def update_status(self, message, color):
        """Updates the status bar text and color safely from any thread."""
        colors = {"blue": self.ACCENT_COLOR, "red": "#E01E1E", "green": "#1FB03A", "orange": self.BUTTON_COLOR}
        self.after(0, lambda: self.status_label.configure(
            text=f"  {message}", 
            text_color=colors.get(color, self.TEXT_COLOR)
        ))
        
    def reset_button(self):
        """Resets the main button to its initial state."""
        self.after(0, lambda: self.get_route_button.configure(
            state="normal", 
            text="IT'S CLOBBERIN' TIME!"
        ))

    # --- Formatting Helper Functions ---
    def format_distance(self, meters):
        if self.unit_var.get() == "metric":
            return f"{meters/1000:.2f} km" if meters >= 1000 else f"{meters:.0f} m"
        else: # imperial
            miles = meters / 1609.34
            return f"{miles:.2f} miles" if miles >= 0.1 else f"{meters * 3.28084:.0f} ft"

    def format_time(self, milliseconds):
        s = milliseconds / 1000
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{int(h)}h {int(m):02d}m" if h > 0 else f"{int(m)}m {int(s):02d}s"

# =======================================================================================
# SECTION 3: APPLICATION LAUNCHER
# =======================================================================================
if __name__ == "__main__":
    api = RouteAPI()  # Create an instance of the backend logic
    app = FantasticRouterApp(api)  # Create the GUI and pass the logic to it
    app.mainloop()