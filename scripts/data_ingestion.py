"""
Data Ingestion Script
Downloads and prepares the Movies Dataset from Kaggle.
"""
import os
import sys
import zipfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


# Configuration
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
KAGGLE_DATASET = "rounakbanik/the-movies-dataset"


def check_kaggle_api():
    """Check if Kaggle API is available and configured."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        return api
    except Exception as e:
        logger.warning(f"Kaggle API not available: {e}")
        return None


def download_dataset(api):
    """Download dataset from Kaggle."""
    logger.info(f"Downloading dataset: {KAGGLE_DATASET}")
    
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    try:
        api.dataset_download_files(
            KAGGLE_DATASET,
            path=RAW_DATA_DIR,
            unzip=True
        )
        logger.info("Dataset downloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to download dataset: {e}")
        return False


def create_sample_data():
    """Create sample data files for testing when Kaggle data is not available."""
    logger.info("Creating sample data for testing...")
    
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    # Sample movies metadata
    movies_data = """adult,belongs_to_collection,budget,genres,homepage,id,imdb_id,original_language,original_title,overview,popularity,poster_path,production_companies,production_countries,release_date,revenue,runtime,spoken_languages,status,tagline,title,video,vote_average,vote_count
False,,30000000,"[{""id"": 28, ""name"": ""Action""}, {""id"": 12, ""name"": ""Adventure""}, {""id"": 878, ""name"": ""Science Fiction""}]",,862,tt0114709,en,Toy Story,"Led by Woody, Andy's toys live happily in his room until Andy's birthday brings Buzz Lightyear onto the scene.",21.946943,/rhIRbceoE9lR4veEXuwCC2wARtG.jpg,,,1995-10-30,373554033,81.0,,Released,,"Toy Story",False,7.7,5415
False,,65000000,"[{""id"": 12, ""name"": ""Adventure""}, {""id"": 14, ""name"": ""Fantasy""}, {""id"": 10751, ""name"": ""Family""}]",,8844,tt0113497,en,Jumanji,"When siblings Judy and Peter discover an enchanted board game that opens the door to a magical world, they unwittingly invite Alan.",17.015539,/vzmL6fP7aPKNKPRTFnZmiUfciyV.jpg,,,1995-12-15,262797249,104.0,,Released,Roll the dice and unleash the excitement!,"Jumanji",False,6.9,2413
False,"{""id"": 119050, ""name"": ""The Dark Knight Collection""}",185000000,"[{""id"": 28, ""name"": ""Action""}, {""id"": 80, ""name"": ""Crime""}, {""id"": 18, ""name"": ""Drama""}]",http://thedarkknight.warnerbros.com/,155,tt0468569,en,The Dark Knight,"Batman raises the stakes in his war on crime with the help of Lt. Jim Gordon and District Attorney Harvey Dent.",187.322927,/qJ2tW6WMUDux911r6m7haRef0WH.jpg,,,2008-07-16,1004558444,152.0,,Released,Why So Serious?,"The Dark Knight",False,8.5,12269
False,"{""id"": 10, ""name"": ""Star Wars Collection""}",11000000,"[{""id"": 12, ""name"": ""Adventure""}, {""id"": 28, ""name"": ""Action""}, {""id"": 878, ""name"": ""Science Fiction""}]",http://www.starwars.com/films/star-wars-episode-iv-a-new-hope,11,tt0076759,en,Star Wars,"Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over the galactic Empire.",126.393695,/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg,,,1977-05-25,775398007,121.0,,Released,A long time ago in a galaxy far far away...,"Star Wars",False,8.1,6778
False,,150000000,"[{""id"": 28, ""name"": ""Action""}, {""id"": 878, ""name"": ""Science Fiction""}, {""id"": 53, ""name"": ""Thriller""}]",http://inceptionmovie.warnerbros.com/,27205,tt1375666,en,Inception,"Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: inception.",83.952389,/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg,,,2010-07-15,825532764,148.0,,Released,Your mind is the scene of the crime,"Inception",False,8.1,14075
False,"{""id"": 230, ""name"": ""The Godfather Collection""}",6000000,"[{""id"": 18, ""name"": ""Drama""}, {""id"": 80, ""name"": ""Crime""}]",http://www.thegodfather.com/,238,tt0068646,en,The Godfather,"Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family.",115.699305,/3bhkrj58Vtu7enYsRolD1fZdja1.jpg,,,1972-03-14,245066411,175.0,,Released,An offer you can't refuse.,"The Godfather",False,8.5,6024
False,,13000000,"[{""id"": 35, ""name"": ""Comedy""}, {""id"": 18, ""name"": ""Drama""}, {""id"": 10749, ""name"": ""Romance""}]",,13,tt0109830,en,Forrest Gump,"A man with a low IQ has accomplished great things in his life and been present during significant historic events—in each case, far exceeding what anyone imagined he could do.",138.133331,/clolk7rB5lAjs41SD0Vt6IXYLMm.jpg,,,1994-07-06,677945399,142.0,,Released,The world will never be the same once you've seen it through the eyes of Forrest Gump.,"Forrest Gump",False,8.2,8147
False,,25000000,"[{""id"": 18, ""name"": ""Drama""}, {""id"": 10749, ""name"": ""Romance""}]",http://www.titanicmovie.com/,597,tt0120338,en,Titanic,"101-year-old Rose DeWitt Bukater tells the story of her life aboard the Titanic, 84 years later.",100.025899,/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg,,,1997-11-18,1845034188,194.0,,Released,Nothing on Earth could come between them.,"Titanic",False,7.5,7770
False,,63000000,"[{""id"": 28, ""name"": ""Action""}, {""id"": 80, ""name"": ""Crime""}, {""id"": 53, ""name"": ""Thriller""}]",http://www.pulpfiction.com,680,tt0110912,en,Pulp Fiction,"A burger-loving hit man, his philosophical partner, a drug-addled gangster's moll and a washed-up boxer converge in this sprawling, comedic crime caper.",140.950236,/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg,,,1994-09-10,213928762,154.0,,Released,Just because you are a character doesn't mean you have character.,"Pulp Fiction",False,8.3,8670
False,,28000000,"[{""id"": 18, ""name"": ""Drama""}]",,278,tt0111161,en,The Shawshank Redemption,"Framed in the 1940s for the double murder of his wife and her lover, upstanding banker Andy Dufresne begins a new life at the Shawshank prison.",51.645403,/9O7gLzmreU0nGkIB6K3BsJbzvNv.jpg,,,1994-09-23,28341469,142.0,,Released,Fear can hold you prisoner. Hope can set you free.,"The Shawshank Redemption",False,8.5,8358"""
    
    # Sample credits
    credits_data = """cast,crew,id
"[{""cast_id"": 14, ""character"": ""Woody (voice)"", ""credit_id"": ""52fe4284c3a36847f8024f95"", ""gender"": 2, ""id"": 31, ""name"": ""Tom Hanks"", ""order"": 0}, {""cast_id"": 15, ""character"": ""Buzz Lightyear (voice)"", ""credit_id"": ""52fe4284c3a36847f8024f99"", ""gender"": 2, ""id"": 12898, ""name"": ""Tim Allen"", ""order"": 1}]","[{""credit_id"": ""52fe4284c3a36847f8024f49"", ""department"": ""Directing"", ""gender"": 2, ""id"": 7879, ""job"": ""Director"", ""name"": ""John Lasseter""}]",862
"[{""cast_id"": 1, ""character"": ""Alan Parrish"", ""credit_id"": ""52fe44bfc3a36847f80a7cd1"", ""gender"": 2, ""id"": 2157, ""name"": ""Robin Williams"", ""order"": 0}]","[{""credit_id"": ""52fe44bfc3a36847f80a7c4b"", ""department"": ""Directing"", ""gender"": 2, ""id"": 8583, ""job"": ""Director"", ""name"": ""Joe Johnston""}]",8844
"[{""cast_id"": 2, ""character"": ""Bruce Wayne / Batman"", ""credit_id"": ""52fe4781c3a36847f81398c3"", ""gender"": 2, ""id"": 3894, ""name"": ""Christian Bale"", ""order"": 0}, {""cast_id"": 3, ""character"": ""Joker"", ""credit_id"": ""52fe4781c3a36847f81398c7"", ""gender"": 2, ""id"": 1810, ""name"": ""Heath Ledger"", ""order"": 1}]","[{""credit_id"": ""52fe4781c3a36847f8139891"", ""department"": ""Directing"", ""gender"": 2, ""id"": 525, ""job"": ""Director"", ""name"": ""Christopher Nolan""}]",155
"[{""cast_id"": 1, ""character"": ""Luke Skywalker"", ""credit_id"": ""52fe420dc3a36847f800a7bd"", ""gender"": 2, ""id"": 2, ""name"": ""Mark Hamill"", ""order"": 0}, {""cast_id"": 2, ""character"": ""Han Solo"", ""credit_id"": ""52fe420dc3a36847f800a7c1"", ""gender"": 2, ""id"": 3, ""name"": ""Harrison Ford"", ""order"": 1}]","[{""credit_id"": ""52fe420dc3a36847f800a77b"", ""department"": ""Directing"", ""gender"": 2, ""id"": 1, ""job"": ""Director"", ""name"": ""George Lucas""}]",11
"[{""cast_id"": 1, ""character"": ""Cobb"", ""credit_id"": ""52fe4534c3a368484e02a311"", ""gender"": 2, ""id"": 6193, ""name"": ""Leonardo DiCaprio"", ""order"": 0}]","[{""credit_id"": ""52fe4534c3a368484e02a2a9"", ""department"": ""Directing"", ""gender"": 2, ""id"": 525, ""job"": ""Director"", ""name"": ""Christopher Nolan""}]",27205
"[{""cast_id"": 1, ""character"": ""Don Vito Corleone"", ""credit_id"": ""52fe4218c3a36847f800b575"", ""gender"": 2, ""id"": 3084, ""name"": ""Marlon Brando"", ""order"": 0}, {""cast_id"": 2, ""character"": ""Michael Corleone"", ""credit_id"": ""52fe4218c3a36847f800b579"", ""gender"": 2, ""id"": 1158, ""name"": ""Al Pacino"", ""order"": 1}]","[{""credit_id"": ""52fe4218c3a36847f800b549"", ""department"": ""Directing"", ""gender"": 2, ""id"": 1776, ""job"": ""Director"", ""name"": ""Francis Ford Coppola""}]",238
"[{""cast_id"": 1, ""character"": ""Forrest Gump"", ""credit_id"": ""52fe420dc3a36847f80051f1"", ""gender"": 2, ""id"": 31, ""name"": ""Tom Hanks"", ""order"": 0}]","[{""credit_id"": ""52fe420dc3a36847f80051bd"", ""department"": ""Directing"", ""gender"": 2, ""id"": 24, ""job"": ""Director"", ""name"": ""Robert Zemeckis""}]",13
"[{""cast_id"": 1, ""character"": ""Rose DeWitt Bukater"", ""credit_id"": ""52fe425a9251416c75039c07"", ""gender"": 1, ""id"": 204, ""name"": ""Kate Winslet"", ""order"": 0}, {""cast_id"": 2, ""character"": ""Jack Dawson"", ""credit_id"": ""52fe425a9251416c75039c0b"", ""gender"": 2, ""id"": 6193, ""name"": ""Leonardo DiCaprio"", ""order"": 1}]","[{""credit_id"": ""52fe425a9251416c75039bd1"", ""department"": ""Directing"", ""gender"": 2, ""id"": 2710, ""job"": ""Director"", ""name"": ""James Cameron""}]",597
"[{""cast_id"": 1, ""character"": ""Vincent Vega"", ""credit_id"": ""52fe4250c3a36847f8012f23"", ""gender"": 2, ""id"": 8891, ""name"": ""John Travolta"", ""order"": 0}, {""cast_id"": 2, ""character"": ""Jules Winnfield"", ""credit_id"": ""52fe4250c3a36847f8012f27"", ""gender"": 2, ""id"": 2231, ""name"": ""Samuel L. Jackson"", ""order"": 1}]","[{""credit_id"": ""52fe4250c3a36847f8012eed"", ""department"": ""Directing"", ""gender"": 2, ""id"": 138, ""job"": ""Director"", ""name"": ""Quentin Tarantino""}]",680
"[{""cast_id"": 1, ""character"": ""Andy Dufresne"", ""credit_id"": ""52fe4231c3a36847f8009d21"", ""gender"": 2, ""id"": 504, ""name"": ""Tim Robbins"", ""order"": 0}, {""cast_id"": 2, ""character"": ""Ellis Boyd 'Red' Redding"", ""credit_id"": ""52fe4231c3a36847f8009d25"", ""gender"": 2, ""id"": 192, ""name"": ""Morgan Freeman"", ""order"": 1}]","[{""credit_id"": ""52fe4231c3a36847f8009cef"", ""department"": ""Directing"", ""gender"": 2, ""id"": 4027, ""job"": ""Director"", ""name"": ""Frank Darabont""}]",278"""
    
    # Sample ratings
    ratings_data = """userId,movieId,rating,timestamp
1,862,4.0,964982703
1,8844,4.0,964981247
1,155,5.0,964982224
1,11,5.0,964982931
2,862,3.5,964982931
2,27205,5.0,964982931
2,238,5.0,964982931
3,862,5.0,964982931
3,155,4.5,964982931
3,13,5.0,964982931
3,597,4.0,964982931
4,680,5.0,964982931
4,278,5.0,964982931
4,238,5.0,964982931
5,155,4.0,964982931
5,27205,4.5,964982931
5,11,5.0,964982931"""
    
    # Write sample files
    with open(RAW_DATA_DIR / "movies_metadata.csv", "w") as f:
        f.write(movies_data)
    
    with open(RAW_DATA_DIR / "credits.csv", "w") as f:
        f.write(credits_data)
    
    with open(RAW_DATA_DIR / "ratings_small.csv", "w") as f:
        f.write(ratings_data)
    
    # Copy ratings_small to ratings
    shutil.copy(RAW_DATA_DIR / "ratings_small.csv", RAW_DATA_DIR / "ratings.csv")
    
    logger.info("Sample data created successfully!")
    logger.info(f"Files created in: {RAW_DATA_DIR}")


def verify_data():
    """Verify that required data files exist."""
    required_files = [
        "movies_metadata.csv",
        "credits.csv",
    ]
    
    optional_files = [
        "ratings.csv",
        "ratings_small.csv",
        "keywords.csv",
    ]
    
    missing_required = []
    missing_optional = []
    
    for f in required_files:
        if not (RAW_DATA_DIR / f).exists():
            missing_required.append(f)
    
    for f in optional_files:
        if not (RAW_DATA_DIR / f).exists():
            missing_optional.append(f)
    
    if missing_required:
        logger.warning(f"Missing required files: {missing_required}")
        return False
    
    if missing_optional:
        logger.info(f"Missing optional files: {missing_optional}")
    
    logger.info("All required data files present!")
    return True


def main():
    """Main function to ingest data."""
    logger.info("Starting data ingestion...")
    
    # Check if data already exists
    if verify_data():
        logger.info("Data already present, skipping download")
        return
    
    # Try Kaggle API
    api = check_kaggle_api()
    
    if api:
        if download_dataset(api):
            verify_data()
            return
    
    # Create sample data as fallback
    logger.info("Creating sample data (Kaggle API not available)")
    create_sample_data()
    
    logger.info("Data ingestion complete!")


if __name__ == "__main__":
    main()

