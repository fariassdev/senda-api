def main():
    """Entry point for running the Senda API server."""
    import uvicorn
    from api import app

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
