# Graphics Project: Helicopter 2D Animation (Pygame)

![helimotion](https://github.com/user-attachments/assets/9724208e-a0c0-4739-80d8-f692923d9a8f)


A professional 2D helicopter animation game in Python using Pygame with full keyboard controls, realistic physics, and dynamic background scrolling.

## Features

- **Keyboard Controls**:
  - **W** - Spin up rotors & ascend (hold to climb)
  - **A** - Move left (background scrolls right)
  - **D** - Move right (background scrolls left)
  - **S** - Initiate landing descent
  - **ESC** - Exit game

- **Game Mechanics**:
  - Rotor spin-up animation before takeoff
  - Physics-based gravity system
  - Smooth altitude-based lift
  - Realistic background parallax scrolling
  - Rotor power indicator (green when ready to fly)
  - Real-time altitude display

- **Visual Effects**:
  - Rotating main and tail rotors
  - Detailed helicopter model with windows and landing skids
  - Parallax background layers (clouds, buildings, trees, grass)
  - Dynamic ground elements
  - Professional HUD display

## State Machine

1. **IDLE** - On ground, rotors stopped
2. **SPINNING UP** - W pressed, rotors accelerating
3. **FLYING** - Full flight control with A/D movement
4. **LANDING** - Controlled descent with S key
5. **SPIN DOWN** - Landed, rotors decelerating

## Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the game:
   ```bash
   python src/main.py
   ```

### Windows quick run

- Double-click [run.bat](run.bat), or from PowerShell:
  ```powershell
  .\run.bat
  ```
  This uses the project venv at .venv automatically, falling back to `python` in PATH.

Tested on Windows with Python 3.9+.

## Game Tuning

Key constants in `src/main.py` for customization:
- `MAX_ROTOR_SPEED` - Maximum rotor RPM
- `SPIN_ACCEL` / `SPIN_DECEL` - Rotor responsiveness
- `MANUAL_VERT_SPEED` - Climb/descent speed
- `MANUAL_HORI_SPEED` - Horizontal movement speed
- `GRAVITY` - Gravitational force when not climbing
