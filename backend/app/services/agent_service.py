class AgentService:
    async def answer(self, message: str) -> dict:
        return {
            "answer": "Natural-language question handling is not implemented yet.",
            "supported": False,
            "message": message,
        }
