"""
Performance Tests
==================

Performance and stress tests for the Scry application.

Test Categories:
- Response time benchmarks
- Memory utilization
- CPU usage
- Concurrent operation tests
- Stress testing
"""

import time
import threading
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.performance
class TestResponseTimeBenchmarks:
    """Performance tests for response times."""

    @pytest.fixture
    def mock_all(self, mocker):
        """Mock all dependencies for performance testing."""
        mock_mss_instance = MagicMock()
        mock_enter = MagicMock()
        mock_mss_instance.__enter__.return_value = mock_enter
        mock_mss_instance.__exit__ = MagicMock(return_value=False)

        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b"\x00" * (1920 * 1080 * 4)
        mock_enter.grab.return_value = mock_sct_img
        mock_enter.monitors = [
            {},
            {"left": 0, "top": 0, "width": 1920, "height": 1080}
        ]

        mocker.patch("mss.mss", return_value=mock_mss_instance)
        mocker.patch("time.sleep")
        mocker.patch("src.main.get_gemini_response", return_value={"type": "SAFE"})
        mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    def test_process_cycle_completes_within_timeout(self, mock_all):
        """Test that process cycle completes within acceptable time."""
        from src.main import process_screen_cycle
        
        start = time.perf_counter()
        process_screen_cycle()
        elapsed = time.perf_counter() - start
        
        # Should complete in under 5 seconds (without actual API call)
        assert elapsed < 5.0

    def test_multiple_cycles_average_time(self, mock_all):
        """Test average time for multiple processing cycles."""
        from src.main import process_screen_cycle
        
        times = []
        for _ in range(10):
            start = time.perf_counter()
            process_screen_cycle()
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Average should be under 1 second (mocked)
        assert avg_time < 1.0


@pytest.mark.performance
class TestMemoryUtilization:
    """Tests for memory usage and leak detection."""

    @pytest.fixture
    def mock_all(self, mocker):
        """Mock all dependencies."""
        mock_mss_instance = MagicMock()
        mock_enter = MagicMock()
        mock_mss_instance.__enter__.return_value = mock_enter
        mock_mss_instance.__exit__ = MagicMock(return_value=False)

        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b"\x00" * (1920 * 1080 * 4)
        mock_enter.grab.return_value = mock_sct_img
        mock_enter.monitors = [
            {},
            {"left": 0, "top": 0, "width": 1920, "height": 1080}
        ]

        mocker.patch("mss.mss", return_value=mock_mss_instance)
        mocker.patch("time.sleep")
        mocker.patch("src.main.get_gemini_response", return_value={"type": "SAFE"})
        mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    @pytest.mark.slow
    def test_no_memory_leak_on_repeated_cycles(self, mock_all):
        """Test that repeated cycles don't leak memory."""
        from src.main import process_screen_cycle
        
        tracemalloc.start()
        
        # Warm up
        for _ in range(5):
            process_screen_cycle()
        
        snapshot1 = tracemalloc.take_snapshot()
        
        # Run more cycles
        for _ in range(50):
            process_screen_cycle()
        
        snapshot2 = tracemalloc.take_snapshot()
        
        tracemalloc.stop()
        
        # Compare top differences
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # Memory increase should be minimal (< 10MB)
        total_increase = sum(stat.size_diff for stat in top_stats[:10])
        assert total_increase < 10 * 1024 * 1024  # 10MB

    def test_large_response_handling_memory(self, mock_all, mocker):
        """Test memory usage with large response texts."""
        # Create a large answer text
        large_answer = "A" * (100 * 1024)  # 100KB
        
        mocker.patch("src.main.get_gemini_response", return_value={
            "type": "DESCRIPTIVE",
            "question": "Test",
            "answer_text": large_answer,
        })
        mocker.patch("src.main.type_text_human_like")
        
        from src.main import process_screen_cycle
        
        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()
        
        process_screen_cycle()
        
        snapshot2 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        
        # Should handle large text without excessive memory use
        # (memory increase should be proportional to text size)


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Tests for concurrent operation performance."""

    def test_config_reload_thread_safety(self, mocker):
        """Test that config reload is thread-safe."""
        mocker.patch("dotenv.load_dotenv")
        
        from src.runtime_config import RuntimeConfig
        
        config = RuntimeConfig()
        errors = []
        
        def reload_config():
            try:
                for _ in range(10):
                    config.reload()
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=reload_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0

    def test_callback_registration_thread_safety(self, mocker):
        """Test that callback registration is thread-safe."""
        from src.runtime_config import RuntimeConfig
        
        config = RuntimeConfig()
        callbacks = []
        errors = []
        
        def register_callback():
            try:
                for i in range(10):
                    cb = lambda k, o, n: None
                    callbacks.append(cb)
                    config.register_callback(f"KEY_{id(cb)}", cb)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=register_callback) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


@pytest.mark.performance
class TestSecurityModulePerformance:
    """Performance tests for security-critical modules."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory."""
        return str(tmp_path)

    @pytest.mark.slow
    def test_encryption_speed(self, temp_dir):
        """Test that encryption completes in acceptable time."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(temp_dir)
        test_key = "TestAPIKey123456789"
        
        times = []
        for _ in range(100):
            start = time.perf_counter()
            manager.encrypt_key(test_key)
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Encryption should be fast (< 50ms average)
        assert avg_time < 0.05

    @pytest.mark.slow
    def test_decryption_speed(self, temp_dir):
        """Test that decryption completes in acceptable time."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(temp_dir)
        test_key = "TestAPIKey123456789"
        encrypted = manager.encrypt_key(test_key)
        
        times = []
        for _ in range(100):
            start = time.perf_counter()
            manager.decrypt_key(encrypted)
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Decryption should be fast (< 50ms average)
        assert avg_time < 0.05


@pytest.mark.performance
class TestTypingEnginePerformance:
    """Performance tests for typing engine."""

    @pytest.fixture
    def typist(self, mocker):
        """Create a HumanTypist instance."""
        mocker.patch("keyboard.on_press_key")
        mocker.patch("src.runtime_config.get_config", return_value=False)
        mocker.patch("time.sleep")
        mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("src.utils.typing_engine._send_vk")
        
        from src.utils.typing_engine import HumanTypist
        return HumanTypist()

    def test_word_complexity_calculation_speed(self, typist):
        """Test that word complexity calculation is fast."""
        words = ["simple", "complexity", "extraordinarily", "test123!@#"]
        
        times = []
        for _ in range(100):
            for word in words:
                start = time.perf_counter()
                typist._calculate_word_complexity(word)
                times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Should be under 1ms
        assert avg_time < 0.001


@pytest.mark.performance
class TestMouseMovementPerformance:
    """Performance tests for mouse movement calculations."""

    def test_path_generation_speed(self, mocker):
        """Test that path generation is fast."""
        mocker.patch("src.utils.mouse.pyautogui")
        
        from src.utils.mouse import _generate_smooth_path_direct
        
        times = []
        for _ in range(100):
            start = time.perf_counter()
            _generate_smooth_path_direct((0, 0), (1000, 1000), 50)
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Path generation should be under 5ms
        assert avg_time < 0.005

    def test_fatigue_factor_calculation_speed(self, mocker):
        """Test that fatigue calculation is fast."""
        mocker.patch("src.utils.mouse.pyautogui")
        
        from src.utils.mouse import _get_fatigue_factor
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            _get_fatigue_factor()
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Should be under 0.1ms
        assert avg_time < 0.0001


@pytest.mark.performance
class TestWebPanelPerformance:
    """Performance tests for web control panel."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client."""
        mocker.patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_config_endpoint_response_time(self, client):
        """Test that config endpoint responds quickly."""
        times = []
        
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/api/config")
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Should respond in under 100ms
        assert avg_time < 0.1

    def test_status_endpoint_response_time(self, client):
        """Test that status endpoint responds quickly."""
        times = []
        
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/api/status")
            times.append(time.perf_counter() - start)
        
        avg_time = sum(times) / len(times)
        
        # Should respond in under 50ms
        assert avg_time < 0.05


@pytest.mark.performance
@pytest.mark.slow
class TestStressTests:
    """Stress tests for system stability."""

    @pytest.fixture
    def mock_all(self, mocker):
        """Mock all dependencies."""
        mock_mss_instance = MagicMock()
        mock_enter = MagicMock()
        mock_mss_instance.__enter__.return_value = mock_enter
        mock_mss_instance.__exit__ = MagicMock(return_value=False)

        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b"\x00" * (1920 * 1080 * 4)
        mock_enter.grab.return_value = mock_sct_img
        mock_enter.monitors = [
            {},
            {"left": 0, "top": 0, "width": 1920, "height": 1080}
        ]

        mocker.patch("mss.mss", return_value=mock_mss_instance)
        mocker.patch("time.sleep")
        mocker.patch("src.main.get_gemini_response", return_value={"type": "SAFE"})
        mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    def test_high_volume_processing(self, mock_all):
        """Test system stability under high processing volume."""
        from src.main import process_screen_cycle
        
        errors = []
        
        for i in range(200):
            try:
                process_screen_cycle()
            except Exception as e:
                errors.append((i, e))
        
        # Should complete without errors
        assert len(errors) == 0



    def test_rapid_mode_toggling(self, mocker):
        """Test stability under rapid mode toggling."""
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src import main
        
        errors = []
        
        for _ in range(100):
            try:
                main.toggle_mode()
            except Exception as e:
                errors.append(e)
        
        assert len(errors) == 0
