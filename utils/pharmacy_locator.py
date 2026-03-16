from typing import List, Dict, Optional
import requests
from utils.utils import setup_logger

logger = setup_logger(__name__)

class PharmacyLocator:
    def __init__(self):
        # OpenStreetMap Headers (Required by their Usage Policy)
        # MUST identify the application uniquely
        self.headers = {
            'User-Agent': 'PharmaBuddy-MedicalApp/1.0 (Student Project; vishalgangisetty@example.com)'
        }
    
    def geocode_address(self, address: str) -> Optional[tuple]:
        """
        Geocode an address using multiple providers for reliability:
        1. Nominatim (OSM)
        2. Photon (Komoot)
        3. OpenMeteo
        """
        # 1. Try Nominatim (Primary)
        coords = self._geocode_nominatim(address)
        if coords:
            return coords
            
        # 2. Try Photon (Fallback 1)
        logger.warning(f"Nominatim failed for '{address}', trying Photon fallback...")
        coords = self._geocode_photon(address)
        if coords:
            return coords

        # 3. Try OpenMeteo (Fallback 2)
        logger.warning(f"Photon failed, trying OpenMeteo fallback...")
        coords = self._geocode_open_meteo(address)
        return coords

    def _geocode_nominatim(self, address: str) -> Optional[tuple]:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1
            }
            # Nominatim STRICTLY requires a unique User-Agent with contact info
            headers = {
                'User-Agent': 'PharmaBuddy-Student-App/1.0 (vishal.student@example.com)'
            }
            response = requests.get(url, params=params, headers=headers, timeout=8)

            if response.status_code != 200:
                logger.warning(f"Nominatim API Status: {response.status_code}")
                return None

            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                try:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    logger.info(f"Nominatim Geocoded '{address}': {lat}, {lon}")
                    return (lat, lon)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Nominatim data parsing error: {e}")
                    return None
            return None
        except requests.Timeout:
            logger.warning(f"Nominatim timeout for '{address}'")
            return None
        except requests.RequestException as e:
            logger.warning(f"Nominatim request error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Nominatim lookup error: {e}")
            return None

    def _geocode_photon(self, address: str) -> Optional[tuple]:
        try:
            url = "https://photon.komoot.io/api/"
            params = {
                "q": address,
                "limit": 1
            }
            # Photon sometimes blocks custom UAs, so use a standard one or the one they recommend
            # But let's try a standard compatible one to avoid 403
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; PharmaBuddy/1.0)'
            }
            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code != 200:
                logger.warning(f"Photon API Status: {response.status_code}")
                return None

            data = response.json()
            if data and data.get('features') and len(data['features']) > 0:
                try:
                    coords = data['features'][0]['geometry']['coordinates']
                    lon = float(coords[0])
                    lat = float(coords[1])
                    logger.info(f"Photon Geocoded '{address}': {lat}, {lon}")
                    return (lat, lon)
                except (ValueError, IndexError, KeyError, TypeError) as e:
                    logger.warning(f"Photon data parsing error: {e}")
                    return None
            return None
        except requests.Timeout:
            logger.warning(f"Photon timeout for '{address}'")
            return None
        except requests.RequestException as e:
            logger.warning(f"Photon request error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Photon lookup error: {e}")
            return None

    def _geocode_open_meteo(self, address: str) -> Optional[tuple]:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": address,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            # OpenMeteo is very reliable
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; PharmaBuddy/1.0)'}
            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code != 200:
                logger.warning(f"OpenMeteo API Status: {response.status_code}")
                return None

            data = response.json()
            if data and 'results' in data and len(data['results']) > 0:
                try:
                    res = data['results'][0]
                    lat = float(res['latitude'])
                    lon = float(res['longitude'])
                    logger.info(f"OpenMeteo Geocoded '{address}': {lat}, {lon}")
                    return (lat, lon)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"OpenMeteo data parsing error: {e}")
                    return None
            return None
        except requests.Timeout:
            logger.warning(f"OpenMeteo timeout for '{address}'")
            return None
        except requests.RequestException as e:
            logger.warning(f"OpenMeteo request error: {e}")
            return None
        except Exception as e:
            logger.error(f"OpenMeteo lookup error: {e}")
            return None
    
    def find_nearby_pharmacies(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        max_results: int = 15
    ) -> List[Dict]:
        """
        Find pharmacies using Overpass API (OpenStreetMap)
        """
        try:
            # Overpass QL query: Find nodes/ways with amenity=pharmacy within radius around lat,lon
            overpass_url = "https://overpass-api.de/api/interpreter"
            search_radius = radius  # meters

            # Query for pharmacies - fixed syntax
            query = f"""
                [out:json];
                (
                  node["amenity"="pharmacy"](around:{search_radius},{latitude},{longitude});
                  way["amenity"="pharmacy"](around:{search_radius},{latitude},{longitude});
                  relation["amenity"="pharmacy"](around:{search_radius},{latitude},{longitude});
                );
                out center limit({max_results});
            """

            response = requests.post(overpass_url, data=query, timeout=(5, 10))

            if response.status_code != 200:
                logger.error(f"Overpass API Error: Status {response.status_code}")
                return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)

            try:
                data = response.json()
            except (ValueError, Exception) as e:
                logger.error(f"Overpass Response Error: {e}")
                return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)

            pharmacies = []
            if data and isinstance(data, dict) and 'elements' in data:
                for element in data.get('elements', []):
                    try:
                        # Handle different element types (node vs way/relation have center)
                        lat = element.get('lat') or element.get('center', {}).get('lat')
                        lon = element.get('lon') or element.get('center', {}).get('lon')

                        if not lat or not lon:
                            continue

                        # Validate coordinates are numbers
                        lat = float(lat)
                        lon = float(lon)

                        tags = element.get('tags', {})
                        name = tags.get('name', 'Unknown Pharmacy')

                        # Format Address from available tags
                        addr_parts = [
                            tags.get('addr:housenumber'),
                            tags.get('addr:street'),
                            tags.get('addr:city'),
                            tags.get('addr:postcode')
                        ]
                        address = ", ".join(filter(None, addr_parts))
                        if not address:
                            address = "Address details not available"

                        # Calculate distance
                        dist = self.calculate_distance(latitude, longitude, lat, lon) * 1000  # to meters

                        pharmacies.append({
                            "name": name,
                            "address": address,
                            "phone": tags.get('phone', tags.get('contact:phone', 'N/A')),
                            "latitude": lat,
                            "longitude": lon,
                            "distance": dist,
                            "rating": "N/A",  # OSM doesn't have ratings
                            "is_open_now": tags.get('opening_hours', 'N/A'),
                            "source": "OpenStreetMap"
                        })
                    except (ValueError, TypeError, KeyError) as e:
                        logger.warning(f"Error processing pharmacy element: {e}")
                        continue

            # Sort by distance
            pharmacies.sort(key=lambda x: x['distance'])

            # Fallback to sample data if empty (OSM might be sparse in some areas)
            if not pharmacies:
                logger.info("No OSM results found, returning sample data.")
                return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)

            return pharmacies

        except requests.Timeout:
            logger.error(f"Overpass API timeout for coordinates {latitude}, {longitude}")
            return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)
        except requests.RequestException as e:
            logger.error(f"Overpass API request error: {e}")
            return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)
        except Exception as e:
            logger.error(f"OSM Search Error: {e}")
            return self._get_sample_pharmacies_with_distance(latitude, longitude, radius)

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km"""
        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def _get_sample_pharmacies_with_distance(self, latitude: float, longitude: float, radius: int) -> List[Dict]:
        """Return sample pharmacies when API is not available or empty"""
        import random
        sample_pharmacies = []
        pharmacy_data = [
            {"name": "Apollo Pharmacy (Sample)", "phone": "+91-9876543210"},
            {"name": "MedPlus (Sample)", "phone": "+91-9876543211"},
            {"name": "Netmeds Store (Sample)", "phone": "+91-9876543212"},
            {"name": "HealthPlus (Sample)", "phone": "+91-9876543213"},
            {"name": "Wellness Forever (Sample)", "phone": "+91-9876543214"}
        ]
        for i, data in enumerate(pharmacy_data):
            offset_lat = random.uniform(-0.01, 0.01)
            offset_lng = random.uniform(-0.01, 0.01)
            distance = random.uniform(500, min(radius, 5000))
            sample_pharmacies.append({
                "name": data["name"],
                "address": f"Sample Address {i+1}, Local Area",
                "phone": data["phone"],
                "latitude": latitude + offset_lat,
                "longitude": longitude + offset_lng,
                "distance": distance,
                "rating": 4.5,
                "is_open_now": True,
                "source": "Sample Data"
            })
        sample_pharmacies.sort(key=lambda x: x['distance'])
        return sample_pharmacies

