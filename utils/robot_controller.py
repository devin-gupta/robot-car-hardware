"""Robot controller for managing motor speeds and velocity control."""
from typing import Dict, Tuple


class RobotController:
    """Manages robot state and calculates motor speeds."""
    
    # Motor speed constraints
    MIN_SPEED = 230
    MAX_SPEED = 255
    VELOCITY_STEP = 5
    TURN_STEP = 15
    
    def __init__(self):
        """Initialize robot controller with zero state."""
        self.base_velocity = 0  # -255 to 255
        self.turn_differential = 0  # accumulated turn difference
    
    def adjust_velocity(self, direction: str) -> Dict[str, int]:
        """
        Adjust base velocity forward or backward.
        
        Args:
            direction: 'up' for forward, 'down' for backward
            
        Returns:
            Dictionary with motor speeds {fl, fr, bl, br}
        """
        if direction == 'up':
            # Increment forward
            if self.base_velocity == 0:
                # Jump directly to minimum valid speed when starting from 0
                self.base_velocity = self.MIN_SPEED
            elif self.base_velocity > 0:
                self.base_velocity = min(self.base_velocity + self.VELOCITY_STEP, self.MAX_SPEED)
            else:
                # Coming from negative, move toward 0
                self.base_velocity = min(self.base_velocity + self.VELOCITY_STEP, 0)
        elif direction == 'down':
            # Decrement or go backward
            if self.base_velocity == 0:
                # Jump directly to minimum valid backward speed when starting from 0
                self.base_velocity = -self.MIN_SPEED
            elif self.base_velocity > 0:
                # Moving from positive toward 0
                self.base_velocity = max(self.base_velocity - self.VELOCITY_STEP, 0)
            else:
                # Moving backward (negative)
                self.base_velocity = max(self.base_velocity - self.VELOCITY_STEP, -self.MAX_SPEED)
        
        # Check if base_velocity is in invalid range (between 0 and MIN_SPEED, or between -MIN_SPEED and 0)
        # If so, set it to 0 to ensure clean zero crossing
        if 0 < self.base_velocity < self.MIN_SPEED:
            self.base_velocity = 0
        elif -self.MIN_SPEED < self.base_velocity < 0:
            self.base_velocity = 0
        
        return self.calculate_motor_speeds()
    
    def adjust_turn(self, direction: str) -> Dict[str, int]:
        """
        Adjust turn differential left or right.
        
        Args:
            direction: 'left' or 'right'
            
        Returns:
            Dictionary with motor speeds {fl, fr, bl, br}
        """
        if direction == 'left':
            self.turn_differential = max(self.turn_differential - self.TURN_STEP, -self.MAX_SPEED)
        elif direction == 'right':
            self.turn_differential = min(self.turn_differential + self.TURN_STEP, self.MAX_SPEED)
        
        return self.calculate_motor_speeds()
    
    def kill_switch(self) -> Dict[str, int]:
        """
        Stop all motors and reset state.
        
        Returns:
            Dictionary with motor speeds {fl: 0, fr: 0, bl: 0, br: 0}
        """
        self.base_velocity = 0
        self.turn_differential = 0
        return self.calculate_motor_speeds()
    
    def constrain_motor_speed(self, speed: int) -> int:
        """
        Constrain motor speed to valid range.
        
        Valid speeds are:
        - Exactly 0
        - 230 to 255 (forward)
        - -230 to -255 (backward)
        
        Args:
            speed: Raw motor speed
            
        Returns:
            Constrained motor speed
        """
        if speed == 0:
            return 0
        
        abs_speed = abs(speed)
        
        # If speed is non-zero but below minimum, set to 0
        if abs_speed < self.MIN_SPEED:
            return 0
        
        # Cap at maximum
        if abs_speed > self.MAX_SPEED:
            return self.MAX_SPEED if speed > 0 else -self.MAX_SPEED
        
        # Ensure it's within valid range
        if self.MIN_SPEED <= abs_speed <= self.MAX_SPEED:
            return speed
        
        return 0
    
    def calculate_motor_speeds(self) -> Dict[str, int]:
        """
        Calculate motor speeds based on current base velocity and turn differential.
        
        Returns:
            Dictionary with motor speeds {fl, fr, bl, br}
        """
        effective_base = self.base_velocity
        
        # Special case: if base is 0 and we're turning, set appropriate base speed
        # to ensure motors meet minimum threshold
        if self.base_velocity == 0 and self.turn_differential != 0:
            # Set base to accommodate turn differential
            # With base=245 and diff=±15: one side=230, other side=255 (after capping)
            abs_diff = abs(self.turn_differential)
            if abs_diff <= 25:
                effective_base = 245  # Works well for typical turn ranges
            else:
                # For very large diffs, adjust base to minimize invalid speeds
                effective_base = max(245, min(255 - abs_diff, 230 + abs_diff))
                if effective_base < 230:
                    effective_base = 245  # Fallback
        
        # Apply turn differential
        # Left motors get +turn_differential, right motors get -turn_differential
        # For left turn (negative diff): left slower, right faster
        # For right turn (positive diff): left faster, right slower
        fl = effective_base + self.turn_differential
        fr = effective_base - self.turn_differential
        bl = effective_base + self.turn_differential
        br = effective_base - self.turn_differential
        
        # Constrain each motor to valid range
        fl = self.constrain_motor_speed(fl)
        fr = self.constrain_motor_speed(fr)
        bl = self.constrain_motor_speed(bl)
        br = self.constrain_motor_speed(br)
        
        # If all motors ended up at 0 when we were trying to turn from 0, reset turn differential
        if (self.base_velocity == 0 and fl == 0 and fr == 0 and bl == 0 and br == 0 
            and self.turn_differential != 0):
            self.turn_differential = 0
            # Recalculate with turn_differential = 0
            fl = fr = bl = br = 0
        
        return {'fl': fl, 'fr': fr, 'bl': bl, 'br': br}
    
    def get_state(self) -> Dict:
        """
        Get current robot state.
        
        Returns:
            Dictionary with base_velocity, turn_differential, and motor speeds
        """
        motors = self.calculate_motor_speeds()
        return {
            'base_velocity': self.base_velocity,
            'turn_differential': self.turn_differential,
            'motors': motors
        }

