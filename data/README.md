# Data Directory

This directory contains raw and processed data for the Movie Recommendation System.

## Directory Structure

```
data/
├── raw/                    # Raw data files (from Kaggle)
│   ├── movies_metadata.csv
│   ├── credits.csv
│   ├── keywords.csv
│   ├── ratings.csv
│   └── ratings_small.csv
├── processed/              # Processed data files
│   ├── movies.csv
│   ├── actors.csv
│   ├── directors.csv
│   ├── genres.csv
│   ├── ratings.csv
│   └── user_item_matrix.pkl
├── models/                 # Trained model files
│   ├── cbf_model.pkl
│   ├── cf_model.pkl
│   └── kgnn_model.pt
└── embeddings/            # Movie embeddings
    └── movie_embeddings.npy
```

## Getting the Data

1. Download "The Movies Dataset" from Kaggle:
   https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset

2. Extract the files to the `raw/` directory

3. Run the preprocessing script:
   ```bash
   python scripts/preprocess.py
   ```

4. Build the Neo4j graph:
   ```bash
   python scripts/graph_build.py
   ```

5. Generate embeddings:
   ```bash
   python scripts/generate_embeddings.py
   ```

## Data Files Description

### Raw Data (from Kaggle)

- **movies_metadata.csv**: Movie information (title, overview, genres, etc.)
- **credits.csv**: Cast and crew information
- **keywords.csv**: Movie keywords
- **ratings.csv**: User ratings (full dataset)
- **ratings_small.csv**: Smaller subset of ratings for testing

### Processed Data

- **movies.csv**: Cleaned movie data with parsed genres
- **actors.csv**: Actor information extracted from credits
- **directors.csv**: Director information extracted from credits
- **genres.csv**: List of all genres
- **ratings.csv**: Processed user ratings

## Notes

- The full ratings dataset is large (~26M ratings). Use `ratings_small.csv` for development.
- Movie IDs are consistent across all files for easy joining.
- Genres are stored as comma-separated values in the processed files.

