# climatedelta
This site aims to show differences in current weather data when compared to historical weather due to climate change. 

To run: 
    `python3 -m app`

TODOs:
    
    * Use https://github.com/symerio/pgeocode for offline city/zip -> lat/lon conversion
        Zip: 
            >>> import pgeocode
            >>> nomi = pgeocode.Nominatim('us') ## save this offline
            >>> nomi.query_postal_code("30306")
        City/State:
            nomi.query_location("Decatur", top_k=1000)["state_name"==STATE]
