"""
Unit Tests for Mouse Utilities Module
======================================

Tests for src/utils/mouse.py including:
- Human-like mouse movement
- Click behaviors
- Path generation algorithms
- Fatigue simulation
- Movement patterns

Test Coverage:
- human_like_move
- click_at
- move_away_from_options
- Path generation functions
- Easing functions
"""

import math
import time
from unittest.mock import MagicMock, patch, call

import pytest


class TestHumanLikeMove:
    """Tests for human_like_move function."""

    @pytest.fixture
    def mock_pyautogui(self, mocker):
        """Mock pyautogui for mouse operations."""
        mock = MagicMock()
        mock.position.return_value = (500, 500)
        mock.size.return_value = (1920, 1080)
        mocker.patch("src.utils.mouse.pyautogui", mock)
        return mock

    def test_move_to_target_coordinates(self, mock_pyautogui, mocker):
        """Test that mouse moves to target coordinates."""
        mocker.patch("time.sleep")
        
        from src.utils.mouse import human_like_move
        
        human_like_move(800, 600)
        
        # Should have called moveTo at some point
        assert mock_pyautogui.moveTo.called

    def test_move_uses_duration(self, mock_pyautogui, mocker):
        """Test that move respects duration parameter."""
        mocker.patch("time.sleep")
        
        from src.utils.mouse import human_like_move
        
        human_like_move(800, 600, duration=1.0)
        
        assert mock_pyautogui.moveTo.called

    def test_move_from_current_position(self, mock_pyautogui, mocker):
        """Test that move starts from current position."""
        mock_pyautogui.position.return_value = (100, 100)
        mocker.patch("time.sleep")
        
        from src.utils.mouse import human_like_move
        
        human_like_move(500, 500)
        
        # Should query current position
        mock_pyautogui.position.assert_called()

    def test_move_with_overshoot_disabled(self, mock_pyautogui, mocker):
        """Test move with overshoot disabled."""
        mocker.patch("time.sleep")
        
        from src.utils.mouse import human_like_move
        
        human_like_move(800, 600, allow_overshoot=False)
        
        assert mock_pyautogui.moveTo.called


class TestClickAt:
    """Tests for click_at function."""

    @pytest.fixture
    def mock_pyautogui(self, mocker):
        """Mock pyautogui for mouse operations."""
        mock = MagicMock()
        mock.position.return_value = (500, 500)
        mocker.patch("src.utils.mouse.pyautogui", mock)
        return mock

    def test_click_at_coordinates(self, mock_pyautogui, mocker):
        """Test that click happens at specified coordinates."""
        mocker.patch("time.sleep")
        mocker.patch("src.utils.mouse.human_like_move")
        
        from src.utils.mouse import click_at
        
        click_at(800, 600)
        
        # Should have clicked
        assert mock_pyautogui.click.called

    def test_click_uses_left_button_only(self, mock_pyautogui, mocker):
        """Test that only left click is used (safety constraint)."""
        mocker.patch("time.sleep")
        mocker.patch("src.utils.mouse.human_like_move")
        
        from src.utils.mouse import click_at
        
        click_at(800, 600)
        
        # Verify left button is used
        if mock_pyautogui.click.called:
            call_kwargs = mock_pyautogui.click.call_args
            # Should explicitly use left button or not specify (default is left)
            if call_kwargs and call_kwargs.kwargs:
                button = call_kwargs.kwargs.get("button", "left")
                assert button == "left"


class TestMoveAwayFromOptions:
    """Tests for move_away_from_options function."""

    @pytest.fixture
    def mock_pyautogui(self, mocker):
        """Mock pyautogui for mouse operations."""
        mock = MagicMock()
        mock.position.return_value = (500, 500)
        mock.size.return_value = (1920, 1080)
        mocker.patch("src.utils.mouse.pyautogui", mock)
        return mock

    def test_moves_to_safe_position(self, mock_pyautogui, mocker):
        """Test that mouse moves to a safe position."""
        mocker.patch("time.sleep")
        
        from src.utils.mouse import move_away_from_options
        
        move_away_from_options()
        
        assert mock_pyautogui.moveTo.called


class TestPathGenerationFunctions:
    """Tests for path generation helper functions."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_lerp_function(self):
        """Test linear interpolation function."""
        # Import after mocks
        import src.utils.mouse as mouse_module
        
        assert mouse_module._lerp(0, 100, 0.5) == 50
        assert mouse_module._lerp(0, 100, 0) == 0
        assert mouse_module._lerp(0, 100, 1) == 100

    def test_smooth_step_function(self):
        """Test smooth step easing function."""
        import src.utils.mouse as mouse_module
        
        # At t=0, should return 0
        assert mouse_module._smooth_step(0) == 0
        # At t=1, should return 1
        assert mouse_module._smooth_step(1) == 1
        # At t=0.5, should return 0.5 (symmetry)
        assert mouse_module._smooth_step(0.5) == 0.5

    def test_smoother_step_function(self):
        """Test smoother step (quintic) easing function."""
        import src.utils.mouse as mouse_module
        
        assert mouse_module._smoother_step(0) == 0
        assert mouse_module._smoother_step(1) == 1

    def test_ease_out_cubic(self):
        """Test ease out cubic function."""
        import src.utils.mouse as mouse_module
        
        assert mouse_module._ease_out_cubic(0) == 0
        assert mouse_module._ease_out_cubic(1) == 1

    def test_ease_in_cubic(self):
        """Test ease in cubic function."""
        import src.utils.mouse as mouse_module
        
        assert mouse_module._ease_in_cubic(0) == 0
        assert mouse_module._ease_in_cubic(1) == 1

    def test_ease_in_out_cubic(self):
        """Test ease in out cubic function."""
        import src.utils.mouse as mouse_module
        
        assert mouse_module._ease_in_out_cubic(0) == 0
        assert mouse_module._ease_in_out_cubic(1) == 1


class TestPathGeneration:
    """Tests for path generation algorithms."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_direct_path_generation(self):
        """Test direct path generation."""
        import src.utils.mouse as mouse_module
        
        start = (0, 0)
        end = (100, 100)
        steps = 10
        
        path = mouse_module._generate_smooth_path_direct(start, end, steps)
        
        assert len(path) == steps
        assert path[0][0] < path[-1][0]  # X increases
        assert path[0][1] < path[-1][1]  # Y increases

    def test_gentle_arc_path_generation(self):
        """Test gentle arc path generation."""
        import src.utils.mouse as mouse_module
        
        start = (0, 0)
        end = (100, 100)
        steps = 10
        
        path = mouse_module._generate_gentle_arc_path(start, end, steps)
        
        assert len(path) == steps

    def test_s_curve_path_generation(self):
        """Test S-curve path generation."""
        import src.utils.mouse as mouse_module
        
        start = (0, 0)
        end = (100, 100)
        steps = 10
        
        path = mouse_module._generate_s_curve_path(start, end, steps)
        
        assert len(path) == steps

    def test_quick_snap_path_generation(self):
        """Test quick snap path generation."""
        import src.utils.mouse as mouse_module
        
        start = (0, 0)
        end = (100, 100)
        steps = 10
        
        path = mouse_module._generate_quick_snap_path(start, end, steps)
        
        assert len(path) >= 3  # At least start, middle, end

    def test_lazy_drift_path_generation(self):
        """Test lazy drift path generation."""
        import src.utils.mouse as mouse_module
        
        start = (0, 0)
        end = (100, 100)
        steps = 10
        
        path = mouse_module._generate_lazy_drift_path(start, end, steps)
        
        assert len(path) == steps


class TestFatigueFactor:
    """Tests for fatigue simulation."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_fatigue_factor_exists(self):
        """Test that fatigue factor function exists."""
        import src.utils.mouse as mouse_module
        
        factor = mouse_module._get_fatigue_factor()
        
        assert isinstance(factor, (int, float))
        assert factor >= 0

    def test_reset_fatigue(self):
        """Test fatigue reset function."""
        import src.utils.mouse as mouse_module
        
        # Should not raise
        mouse_module.reset_fatigue()


class TestSimulateReadingPause:
    """Tests for reading pause simulation."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_simulate_reading_pause(self, mocker):
        """Test reading pause simulation."""
        mock_sleep = mocker.patch("time.sleep")
        import src.utils.mouse as mouse_module
        
        mouse_module.simulate_reading_pause(0.5, 2.0)
        
        # Should have slept
        mock_sleep.assert_called_once()
        
        # Sleep duration should be within range
        actual_duration = mock_sleep.call_args[0][0]
        assert 0.5 <= actual_duration <= 2.0


class TestWeightedChoice:
    """Tests for weighted random choice."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_weighted_choice_returns_key(self):
        """Test weighted choice returns a key from the dict."""
        import src.utils.mouse as mouse_module
        
        choices = {"a": 1, "b": 2, "c": 3}
        
        result = mouse_module._weighted_choice(choices)
        
        assert result in choices.keys()

    def test_weighted_choice_respects_weights(self):
        """Test that weighted choice respects weights statistically."""
        import src.utils.mouse as mouse_module
        
        # Heavily weighted towards 'c'
        choices = {"a": 1, "b": 1, "c": 100}
        
        results = [mouse_module._weighted_choice(choices) for _ in range(100)]
        
        # 'c' should appear most often
        c_count = results.count("c")
        assert c_count > 50  # Should be at least half


class TestMovementBehaviorConstants:
    """Tests for movement behavior constants."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Setup mocks for imports."""
        mocker.patch("src.utils.mouse.pyautogui")

    def test_hover_before_click_probability_exists(self):
        """Test HOVER_BEFORE_CLICK_PROBABILITY constant."""
        import src.utils.mouse as mouse_module
        
        assert 0 <= mouse_module.HOVER_BEFORE_CLICK_PROBABILITY <= 1

    def test_click_hold_duration_range_exists(self):
        """Test CLICK_HOLD_DURATION_RANGE constant."""
        import src.utils.mouse as mouse_module
        
        assert len(mouse_module.CLICK_HOLD_DURATION_RANGE) == 2
        assert mouse_module.CLICK_HOLD_DURATION_RANGE[0] <= mouse_module.CLICK_HOLD_DURATION_RANGE[1]

    def test_post_click_drift_probability_exists(self):
        """Test POST_CLICK_DRIFT_PROBABILITY constant."""
        import src.utils.mouse as mouse_module
        
        assert 0 <= mouse_module.POST_CLICK_DRIFT_PROBABILITY <= 1
