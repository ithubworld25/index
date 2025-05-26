from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import generator
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.post("/parse")
async def parse(request: Request):
    text = (await request.body()).decode()
    xml = generator.generate_bpmn(text)
    return JSONResponse({"bpmn": xml})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
