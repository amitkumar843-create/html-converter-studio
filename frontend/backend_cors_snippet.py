# Add this import near your other FastAPI imports
from fastapi.middleware.cors import CORSMiddleware

# Add this immediately after: app = FastAPI(...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
