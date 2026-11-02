from pyrplidar import PyRPlidar
import time

PORT = "/dev/cu.usbserial-110"      # Change to your port
BAUD = 460800      # C1 specific baudrate

def run_lidar():
    lidar = PyRPlidar()

    # NOTE: RPLIDAR C1 usually requires 460800 baudrate

    try:
        # Connect to the LiDAR
        lidar.connect(port=PORT, baudrate=BAUD, timeout=3)

        # Start the motor
        lidar.set_motor_pwm(600) # Standard speed
        time.sleep(2) # Give it a moment to spin up
        lidar.get_info() # Fetching info first can "wake up" the serial sync

        print("Starting scan... Press Ctrl+C to stop.")

        # Create a scan generator
        # 'force_scan' is often more reliable for raw data printing
        # scan_generator = lidar.force_scan()
        scan_generator = lidar.start_scan()

        for count, scan in enumerate(scan_generator()):
            # scan is a 'RPlidarMeasurement' object
            angle = scan.angle
            distance = scan.distance # Distance in mm

            # Filter out zero-distance (failed) readings
            if distance > 0:
                print(f"Angle: {angle:6.2f}° | Distance: {distance:8.2f} mm")

            # Optional: Add a small break or limit count to avoid flooding the console
            if count > 500:
                break

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Instead of lidar.stop_motor()
        lidar.set_motor_pwm(0)
        lidar.disconnect()
        print("LiDAR disconnected and motor stopped.")

if __name__ == "__main__":
    run_lidar()