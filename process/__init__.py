import uvicorn
from .api import app


def main():
    uvicorn.run(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()
