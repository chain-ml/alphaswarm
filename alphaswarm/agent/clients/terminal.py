import asyncio

from alphaswarm.agent.agent import AlphaSwarmAgentManager


class TerminalClient:
    def __init__(self, manager: AlphaSwarmAgentManager, client_id: str):
        self._manager = manager
        self.client_id = client_id

    async def start(self):
        await self.manager.register_client(self.client_id)
        try:
            while True:
                message = await asyncio.get_event_loop().run_in_executor(None, input, f"{self.client_id}> ")
                if message.lower() == "quit":
                    break
                response = await self._manager.handle_message(self.client_id, message)
                print(f"Response: {response}")
        finally:
            await self._manager.unregister_client(self.client_id)
