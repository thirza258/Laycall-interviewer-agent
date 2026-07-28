import pytest


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, test_client):
        """Health check endpoint should return 200 with status and env."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "env" in data

    @pytest.mark.asyncio
    async def test_health_check_response_format(self, test_client):
        """Health check response should contain required fields."""
        response = await test_client.get("/health")

        data = response.json()
        assert isinstance(data["status"], str)
        assert data["status"] == "healthy"
        assert isinstance(data["env"], str)
        assert len(data) == 2
