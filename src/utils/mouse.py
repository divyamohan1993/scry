"""
Mouse Utilities - Human-like mouse movement and clicking.

SAFETY CONSTRAINT: This module ONLY performs LEFT CLICKS.
Right-clicks are NEVER performed under any circumstance.
All click operations explicitly specify button='left'.
"""
import math
import random
import time

import pyautogui

from ..logger import get_logger

logger = get_logger("MouseUtils")

# =============================================================================
# MOVEMENT STYLE WEIGHTS - Controls variety of movement types
# =============================================================================

# Movement styles and their relative weights (higher = more likely)
MOVEMENT_STYLES = {
    "smooth_direct": 25,      # Smooth straight-ish line (touchpad swipe)
    "gentle_arc": 20,         # Subtle curved path
    "s_curve": 10,            # S-shaped path (dodge obstacles mentally)
    "lazy_drift": 8,          # Slow, meandering movement
    "quick_snap": 12,         # Fast, almost instant (flick)
    "hesitant": 8,            # Slow start, then commits
    "overshoot_correct": 7,   # Goes past, then backs up
    "two_phase": 10,          # Pause midway, then continue
}

# =============================================================================
# CLICK BEHAVIOR CONSTANTS
# =============================================================================

HOVER_BEFORE_CLICK_PROBABILITY = 0.25
HOVER_DURATION_RANGE = (0.08, 0.35)
DOUBLE_CLICK_MISTAKE_PROBABILITY = 0.015
CLICK_HOLD_DURATION_RANGE = (0.04, 0.10)
POST_CLICK_DRIFT_PROBABILITY = 0.35
POST_CLICK_DRIFT_RANGE = (1, 5)

# Fatigue tracking
_interaction_count = 0


def _get_fatigue_factor():
    """Returns a subtle fatigue factor."""
    global _interaction_count
    return min(_interaction_count * 0.003, 0.08)


def _weighted_choice(choices_dict):
    """Select a key from dict based on weight values."""
    items = list(choices_dict.items())
    total = sum(w for _, w in items)
    r = random.uniform(0, total)
    cumulative = 0
    for key, weight in items:
        cumulative += weight
        if r <= cumulative:
            return key
    return items[-1][0]


def _lerp(a, b, t):
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def _smooth_step(t):
    """Hermite smoothstep for butter-smooth interpolation."""
    return t * t * (3 - 2 * t)


def _smoother_step(t):
    """Even smoother (quintic) interpolation."""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _ease_out_cubic(t):
    """Decelerating to zero velocity."""
    return 1 - pow(1 - t, 3)


def _ease_in_cubic(t):
    """Accelerating from zero velocity."""
    return t * t * t


def _ease_in_out_cubic(t):
    """Acceleration until halfway, then deceleration."""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def _generate_smooth_path_direct(start, end, steps):
    """Generate smooth direct path (like touchpad swipe)."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Use smoother_step for butter-smooth movement
        smooth_t = _smoother_step(t)
        x = _lerp(start[0], end[0], smooth_t)
        y = _lerp(start[1], end[1], smooth_t)
        points.append((x, y))
    return points


def _generate_gentle_arc_path(start, end, steps):
    """Generate gentle arc path with subtle curve."""
    points = []
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)
    
    # Very subtle arc - perpendicular offset
    perp_x, perp_y = -dy, dx
    norm = math.hypot(perp_x, perp_y) or 1
    perp_x, perp_y = perp_x / norm, perp_y / norm
    
    # Random arc direction and small magnitude
    arc_magnitude = dist * random.uniform(0.05, 0.15) * random.choice([-1, 1])
    
    for i in range(steps + 1):
        t = i / steps
        smooth_t = _smooth_step(t)
        
        # Arc peaks at middle of movement
        arc_factor = math.sin(t * math.pi) * arc_magnitude
        
        x = _lerp(start[0], end[0], smooth_t) + perp_x * arc_factor
        y = _lerp(start[1], end[1], smooth_t) + perp_y * arc_factor
        points.append((x, y))
    return points


def _generate_s_curve_path(start, end, steps):
    """Generate S-curve path."""
    points = []
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)
    
    perp_x, perp_y = -dy, dx
    norm = math.hypot(perp_x, perp_y) or 1
    perp_x, perp_y = perp_x / norm, perp_y / norm
    
    s_magnitude = dist * random.uniform(0.08, 0.18)
    
    for i in range(steps + 1):
        t = i / steps
        smooth_t = _smoother_step(t)
        
        # S-curve: sin(2*pi*t) creates the double-wave
        s_factor = math.sin(t * math.pi * 2) * s_magnitude * (1 - abs(t - 0.5) * 2)
        
        x = _lerp(start[0], end[0], smooth_t) + perp_x * s_factor
        y = _lerp(start[1], end[1], smooth_t) + perp_y * s_factor
        points.append((x, y))
    return points


def _generate_lazy_drift_path(start, end, steps):
    """Generate slow, wandering path."""
    points = []
    
    # Create 2-3 random waypoints
    num_waypoints = random.randint(2, 3)
    waypoints = [start]
    
    for i in range(num_waypoints):
        progress = (i + 1) / (num_waypoints + 1)
        base_x = _lerp(start[0], end[0], progress)
        base_y = _lerp(start[1], end[1], progress)
        # Small random offset
        offset = random.uniform(10, 30) * random.choice([-1, 1])
        waypoints.append((base_x + offset * random.uniform(-1, 1), 
                         base_y + offset * random.uniform(-1, 1)))
    waypoints.append(end)
    
    # Interpolate through waypoints smoothly
    points_per_segment = steps // len(waypoints)
    for seg in range(len(waypoints) - 1):
        seg_start = waypoints[seg]
        seg_end = waypoints[seg + 1]
        for i in range(points_per_segment):
            t = i / points_per_segment
            smooth_t = _smooth_step(t)
            x = _lerp(seg_start[0], seg_end[0], smooth_t)
            y = _lerp(seg_start[1], seg_end[1], smooth_t)
            points.append((x, y))
    
    points.append(end)
    return points


def _generate_quick_snap_path(start, end, steps):
    """Generate fast snap movement - few points, quick timing."""
    # Use fewer effective points for snappier feel
    actual_steps = max(5, steps // 4)
    points = []
    
    for i in range(actual_steps + 1):
        t = i / actual_steps
        # Ease out - fast start, slow end
        smooth_t = _ease_out_cubic(t)
        x = _lerp(start[0], end[0], smooth_t)
        y = _lerp(start[1], end[1], smooth_t)
        points.append((x, y))
    return points


def _generate_hesitant_path(start, end, steps):
    """Generate hesitant movement - slow then fast."""
    points = []
    
    for i in range(steps + 1):
        t = i / steps
        # Custom easing: very slow start (cubic in), fast finish
        if t < 0.4:
            # Slow initial phase
            smooth_t = _ease_in_cubic(t / 0.4) * 0.2
        else:
            # Fast commit phase
            remaining = (t - 0.4) / 0.6
            smooth_t = 0.2 + _ease_out_cubic(remaining) * 0.8
        
        x = _lerp(start[0], end[0], smooth_t)
        y = _lerp(start[1], end[1], smooth_t)
        points.append((x, y))
    return points


def _generate_overshoot_path(start, end, steps):
    """Generate path that overshoots then corrects."""
    points = []
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    overshoot_amount = random.uniform(0.08, 0.15)
    overshoot_point = (end[0] + dx * overshoot_amount, 
                       end[1] + dy * overshoot_amount)
    
    # First phase: go past target (70% of steps)
    phase1_steps = int(steps * 0.7)
    for i in range(phase1_steps):
        t = i / phase1_steps
        smooth_t = _ease_out_cubic(t)
        x = _lerp(start[0], overshoot_point[0], smooth_t)
        y = _lerp(start[1], overshoot_point[1], smooth_t)
        points.append((x, y))
    
    # Second phase: correct back (30% of steps)
    phase2_steps = steps - phase1_steps
    for i in range(phase2_steps + 1):
        t = i / phase2_steps
        smooth_t = _ease_in_out_cubic(t)
        x = _lerp(overshoot_point[0], end[0], smooth_t)
        y = _lerp(overshoot_point[1], end[1], smooth_t)
        points.append((x, y))
    
    return points


def _generate_two_phase_path(start, end, steps):
    """Generate path with pause in middle."""
    points = []
    
    # Midpoint with slight random offset
    mid = (
        _lerp(start[0], end[0], 0.5) + random.uniform(-15, 15),
        _lerp(start[1], end[1], 0.5) + random.uniform(-15, 15)
    )
    
    half_steps = steps // 2
    
    # First half
    for i in range(half_steps):
        t = i / half_steps
        smooth_t = _smoother_step(t)
        x = _lerp(start[0], mid[0], smooth_t)
        y = _lerp(start[1], mid[1], smooth_t)
        points.append((x, y))
    
    # Add "pause" points at midpoint
    pause_points = random.randint(3, 8)
    for _ in range(pause_points):
        points.append(mid)
    
    # Second half
    for i in range(half_steps + 1):
        t = i / half_steps
        smooth_t = _smoother_step(t)
        x = _lerp(mid[0], end[0], smooth_t)
        y = _lerp(mid[1], end[1], smooth_t)
        points.append((x, y))
    
    return points


def human_like_move(target_x, target_y, duration=None, allow_overshoot=True):
    """
    Moves mouse to (x, y) using dynamically selected movement style.
    Each movement is unique - no predictable patterns.
    Smooth like touchpad movement, no jitter.
    """
    global _interaction_count
    _interaction_count += 1
    
    start_x, start_y = pyautogui.position()
    dist = math.hypot(target_x - start_x, target_y - start_y)
    
    # Early exit for tiny movements
    if dist < 3:
        pyautogui.moveTo(target_x, target_y)
        return
    
    # Randomly select movement style
    style = _weighted_choice(MOVEMENT_STYLES)
    
    # Dynamic duration based on style and distance
    if duration is None:
        base_duration = 0.15 + (dist / 1500)  # Base: faster for short, slower for long
        
        if style == "quick_snap":
            duration = base_duration * random.uniform(0.3, 0.5)
        elif style == "lazy_drift":
            duration = base_duration * random.uniform(1.8, 2.5)
        elif style == "hesitant":
            duration = base_duration * random.uniform(1.2, 1.6)
        else:
            duration = base_duration * random.uniform(0.7, 1.3)
        
        # Cap duration
        duration = max(0.08, min(duration, 1.5))
    
    # Calculate steps based on duration (smooth ~60fps feel)
    steps = max(8, int(duration * 60))
    
    start = (start_x, start_y)
    end = (target_x, target_y)
    
    # Generate path based on selected style
    if style == "smooth_direct":
        points = _generate_smooth_path_direct(start, end, steps)
    elif style == "gentle_arc":
        points = _generate_gentle_arc_path(start, end, steps)
    elif style == "s_curve":
        points = _generate_s_curve_path(start, end, steps)
    elif style == "lazy_drift":
        points = _generate_lazy_drift_path(start, end, steps)
    elif style == "quick_snap":
        points = _generate_quick_snap_path(start, end, steps)
    elif style == "hesitant":
        points = _generate_hesitant_path(start, end, steps)
    elif style == "overshoot_correct":
        points = _generate_overshoot_path(start, end, steps)
    elif style == "two_phase":
        points = _generate_two_phase_path(start, end, steps)
    else:
        points = _generate_smooth_path_direct(start, end, steps)
    
    # Calculate timing per point
    step_delay = duration / len(points) if points else 0.01
    
    # Execute movement - smooth, no jitter
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0
    
    try:
        for x, y in points:
            pyautogui.moveTo(x, y)
            time.sleep(step_delay)
    finally:
        pyautogui.PAUSE = original_pause
    
    # Ensure we end exactly at target
    pyautogui.moveTo(target_x, target_y)
    logger.debug(f"Mouse moved ({style}) to ({target_x}, {target_y})")


def smooth_move(x, y, duration=None):
    """Wrapper for human_like_move."""
    human_like_move(x, y, duration)


def click_at(x, y):
    """
    Click at coordinates with human-like behavior.
    LEFT CLICK ONLY - never right click.
    """
    # Random offset for click position
    offset_x = x + random.randint(-4, 4)
    offset_y = y + random.randint(-4, 4)
    
    # Move to target
    smooth_move(offset_x, offset_y)
    
    # Optional hover before click
    if random.random() < HOVER_BEFORE_CLICK_PROBABILITY:
        time.sleep(random.uniform(*HOVER_DURATION_RANGE))
    else:
        time.sleep(random.uniform(0.03, 0.12))
    
    # Perform LEFT click only
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0
    try:
        pyautogui.mouseDown(button='left')
        time.sleep(random.uniform(*CLICK_HOLD_DURATION_RANGE))
        pyautogui.mouseUp(button='left')
        
        # Rare accidental double-click
        if random.random() < DOUBLE_CLICK_MISTAKE_PROBABILITY:
            time.sleep(random.uniform(0.04, 0.10))
            pyautogui.mouseDown(button='left')
            time.sleep(random.uniform(0.02, 0.06))
            pyautogui.mouseUp(button='left')
            logger.debug("Accidental double-click")
    finally:
        pyautogui.PAUSE = original_pause
    
    # Post-click drift
    if random.random() < POST_CLICK_DRIFT_PROBABILITY:
        drift_x = offset_x + random.uniform(-POST_CLICK_DRIFT_RANGE[1], POST_CLICK_DRIFT_RANGE[1])
        drift_y = offset_y + random.uniform(-POST_CLICK_DRIFT_RANGE[1], POST_CLICK_DRIFT_RANGE[1])
        time.sleep(random.uniform(0.01, 0.04))
        pyautogui.moveTo(drift_x, drift_y)
    
    logger.info(f"Clicked at ({offset_x}, {offset_y})")


def move_away_from_options():
    """
    Move mouse to random safe screen position after selecting answer.
    Uses varied movement styles for unpredictability.
    """
    screen_width, screen_height = pyautogui.size()
    
    # Safe zone: 20% margin from edges
    margin_x = int(screen_width * 0.2)
    margin_y = int(screen_height * 0.2)
    
    target_x = random.randint(margin_x, screen_width - margin_x)
    target_y = random.randint(margin_y, screen_height - margin_y)
    
    # Random delay before moving
    delay_type = random.random()
    if delay_type < 0.15:
        time.sleep(random.uniform(0.05, 0.15))  # Quick
    elif delay_type < 0.35:
        time.sleep(random.uniform(0.4, 0.8))    # Slow/thinking
    else:
        time.sleep(random.uniform(0.15, 0.35))  # Normal
    
    # Sometimes move in stages
    if random.random() < 0.2:
        mid_x = (pyautogui.position()[0] + target_x) // 2 + random.randint(-40, 40)
        mid_y = (pyautogui.position()[1] + target_y) // 2 + random.randint(-40, 40)
        mid_x = max(margin_x, min(screen_width - margin_x, mid_x))
        mid_y = max(margin_y, min(screen_height - margin_y, mid_y))
        
        human_like_move(mid_x, mid_y)
        time.sleep(random.uniform(0.03, 0.12))
    
    human_like_move(target_x, target_y)
    logger.debug(f"Moved away to ({target_x}, {target_y})")


def simulate_reading_pause(min_seconds=0.5, max_seconds=2.0):
    """Simulate human reading/thinking pause."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def reset_fatigue():
    """Reset fatigue counter for new session."""
    global _interaction_count
    _interaction_count = 0
    logger.debug("Fatigue reset")
