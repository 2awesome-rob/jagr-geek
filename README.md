# jagr-geek
This repository houses a simple streamlit frontend app for Rob's Junior Hockey Programs.
It directly access the backend database and displays simple game/player statistics.

## Features
- Streamlit UI
- Plotly Express chartlets

## 📂 Structure
```text
jagr-geek/
│
├── streamlit_app.py		# UI and Streamlit entry point
├── .streamlit
│	└── config.toml			# Global Theme settings
├── app/
│	├── services/			# display and logic services
│	|	├── player.py
│	|	├── plots.py
│	|	└── team.py
│	├── utils/				# helper functions
│	└── database/			# Database access point
├── tests/				  	# TODO add testing
│	├── test.db				# Test Database
│	├── conftest.py			# CI test setup
│	└── test_*.py			# CI tests
├── scripts/
├── requirements.txt
├── .env.example
└── README.md
```

## Architecture
A simple Streamlit app showing hockey stats from a database.
Deployed as [Rocket Hockey](https://rocket-hockey.streamlit.app/) hosted by StreamLit.

### Database configuration

The app reads `DATABASE_URL` from the process environment first, then from a local `.env` file for development testing. If neither is set, it uses `tests/test.db`.

Enter `DATABASE_URL=postgresql+psycopg2://...` in streamlit secrets for deployment.


### Development
- Setup:
```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

- Run:
```powershell
$ streamlit run streamlit_app.py
```
