import tkinter as tk
from tkinter import messagebox, ttk
import requests
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class WeatherData:
    """Class to handle weather data fetching and processing"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"  

        
    def fetch_weather(self, city=None, lat=None, lon=None):
        """Fetch weather data from OpenWeatherMap API"""
        try:
            if city:
                url = f"{self.base_url}?q={city}&appid={self.api_key}&units=metric"
            elif lat and lon:
                url = f"{self.base_url}?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            else:
                return None, "Please provide a city name or coordinates."
            
            response = requests.get(url)
            response.raise_for_status()  # Raises an exception for HTTP errors (e.g., 401)
            data = response.json()
            
            if data.get("cod") != 200:
                return None, data.get("message", "Error fetching weather data.")
            
            return {
                "city": data["name"],
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        except requests.RequestException as e:
            return None, f"Network error: {str(e)}"
        except KeyError as e:
            return None, f"Data parsing error: Missing key {str(e)}"

class DatabaseManager:
    """Class to handle SQLite database operations"""
    def __init__(self, db_name="weather_app.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Create tables for favorite locations and weather history"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL UNIQUE,
                lat REAL,
                lon REAL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                temp REAL,
                humidity INTEGER,
                wind_speed REAL,
                description TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def add_favorite(self, city, lat, lon):
        """Add a city to favorites"""
        try:
            self.cursor.execute(
                "INSERT INTO favorites (city, lat, lon) VALUES (?, ?, ?)",
                (city, lat, lon)
            )
            self.conn.commit()
            return True, "City added to favorites."
        except sqlite3.IntegrityError:
            return False, "City already in favorites."

    def remove_favorite(self, city):
        """Remove a city from favorites"""
        self.cursor.execute("DELETE FROM favorites WHERE city = ?", (city,))
        self.conn.commit()
        return self.cursor.rowcount > 0, "City removed." if self.cursor.rowcount > 0 else "City not found."

    def get_favorites(self):
        """Retrieve all favorite cities"""
        self.cursor.execute("SELECT city, lat, lon FROM favorites")
        return self.cursor.fetchall()

    def save_weather_history(self, weather_data):
        """Save weather data to history"""
        self.cursor.execute(
            "INSERT INTO weather_history (city, temp, humidity, wind_speed, description, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                weather_data["city"],
                weather_data["temp"],
                weather_data["humidity"],
                weather_data["wind_speed"],
                weather_data["description"],
                weather_data["timestamp"]
            )
        )
        self.conn.commit()

    def get_weather_history(self, city):
        """Retrieve weather history for a city"""
        self.cursor.execute(
            "SELECT temp, humidity, wind_speed, description, timestamp FROM weather_history WHERE city = ?",
            (city,)
        )
        return self.cursor.fetchall()

    def close(self):
        """Close database connection"""
        self.conn.close()

class WeatherApp:
    """Main application class for the Tkinter GUI"""
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Forecasting App")
        self.root.geometry("800x600")
        self.weather_data = WeatherData("cb2d71f2983036746e39acc3dafa4bd3")  # Your API key
        self.db = DatabaseManager()
        self.setup_gui()

    def setup_gui(self):
        """Set up the Tkinter GUI"""
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Search section
        ttk.Label(self.main_frame, text="Enter City:").grid(row=0, column=0, sticky=tk.W)
        self.city_entry = ttk.Entry(self.main_frame, width=30)
        self.city_entry.grid(row=0, column=1, sticky=tk.W)
        self.city_entry.bind("<Return>", self.search_weather_event)  # Event handling for Enter key

        ttk.Button(self.main_frame, text="Search", command=self.search_weather).grid(row=0, column=2, padx=5)
        ttk.Button(self.main_frame, text="Add to Favorites", command=self.add_to_favorites).grid(row=0, column=3, padx=5)

        # Weather display
        self.weather_label = ttk.Label(self.main_frame, text="Weather Info: Enter a city to see details.", wraplength=700)
        self.weather_label.grid(row=1, column=0, columnspan=4, pady=10)

        # Favorites section
        ttk.Label(self.main_frame, text="Favorite Cities:").grid(row=2, column=0, sticky=tk.W)
        self.favorites_listbox = tk.Listbox(self.main_frame, width=30, height=5)
        self.favorites_listbox.grid(row=3, column=0, columnspan=2, pady=5)
        self.favorites_listbox.bind("<<ListboxSelect>>", self.show_favorite_weather)  # Event handling for listbox selection

        ttk.Button(self.main_frame, text="Remove Selected", command=self.remove_favorite).grid(row=3, column=2, padx=5)
        ttk.Button(self.main_frame, text="Show History Graph", command=self.show_history_graph).grid(row=3, column=3, padx=5)

        # Graph canvas
        self.canvas_frame = ttk.Frame(self.main_frame)
        self.canvas_frame.grid(row=4, column=0, columnspan=4, pady=10)

        self.update_favorites_list()

    def search_weather(self):
        """Search weather for the entered city"""
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name.")
            return

        weather, error = self.weather_data.fetch_weather(city=city)
        if error:
            messagebox.showerror("Error", error)
            return

        self.display_weather(weather)
        self.db.save_weather_history(weather)

    def search_weather_event(self, event):
        """Handle Enter key press for search"""
        self.search_weather()

    def display_weather(self, weather):
        """Display weather data in the GUI"""
        text = (
            f"City: {weather['city']}\n"
            f"Temperature: {weather['temp']}°C\n"
            f"Humidity: {weather['humidity']}%\n"
            f"Wind Speed: {weather['wind_speed']} m/s\n"
            f"Description: {weather['description'].capitalize()}\n"
            f"Time: {weather['timestamp']}"
        )
        self.weather_label.config(text=text)

    def add_to_favorites(self):
        """Add current city to favorites"""
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name.")
            return

        weather, error = self.weather_data.fetch_weather(city=city)
        if error:
            messagebox.showerror("Error", error)
            return

        success, message = self.db.add_favorite(weather['city'], weather['lat'], weather['lon'])
        messagebox.showinfo("Result", message)
        if success:
            self.update_favorites_list()

    def remove_favorite(self):
        """Remove selected city from favorites"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a city to remove.")
            return

        city = self.favorites_listbox.get(selection[0]).split(" (")[0]
        success, message = self.db.remove_favorite(city)
        messagebox.showinfo("Result", message)
        if success:
            self.update_favorites_list()

    def update_favorites_list(self):
        """Update the favorites listbox"""
        self.favorites_listbox.delete(0, tk.END)
        for city, lat, lon in self.db.get_favorites():
            self.favorites_listbox.insert(tk.END, f"{city} ({lat}, {lon})")

    def show_favorite_weather(self, event):
        """Display weather for selected favorite city"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            return

        city = self.favorites_listbox.get(selection[0]).split(" (")[0]
        weather, error = self.weather_data.fetch_weather(city=city)
        if error:
            messagebox.showerror("Error", error)
            return

        self.display_weather(weather)
        self.db.save_weather_history(weather)

    def show_history_graph(self):
        """Display historical weather data in a graph"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a city to view history.")
            return

        city = self.favorites_listbox.get(selection[0]).split(" (")[0]
        history = self.db.get_weather_history(city)
        if not history:
            messagebox.showinfo("Info", f"No weather history for {city}.")
            return

        # Prepare data for plotting
        temps, humidities, timestamps = [], [], []
        for temp, humidity, wind_speed, desc, timestamp in history:
            temps.append(temp)
            humidities.append(humidity)
            timestamps.append(timestamp)

        # Create plot
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(timestamps, temps, label="Temperature (°C)", marker="o")
        ax.plot(timestamps, humidities, label="Humidity (%)", marker="s")
        ax.set_title(f"Weather History for {city}")
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Value")
        ax.legend()
        ax.tick_params(axis="x", rotation=45)

        # Embed plot in Tkinter
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()
        plt.close(fig)  

    def __del__(self):
        """Clean up database connection"""
        self.db.close()

def main():
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()