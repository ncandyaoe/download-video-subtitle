import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",  # 使用字符串引用应用
        #host="0.0.0.0",
        port=7878,
        reload=True  # 启用热重载
    ) 