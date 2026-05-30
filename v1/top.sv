// Top-level module: LiDAR maze robot FPGA pipeline
//
// Connections:
//   Pmod JA pin1 (G13) = lidar_rx   (LiDAR yellow TX wire)
//   Pmod JA pin2 (B11) = lidar_tx   (LiDAR green  RX wire)
//   Pmod JB pin1 (E15) = arduino_tx (to Arduino pin 19 / Serial1 RX)
//   Pmod JB pin2 (E16) = arduino_rx (from Arduino pin 18 via 1k+2k divider)
//   USB-UART A9 = debug_tx (115200 baud — forwards raw LiDAR bytes to PC)
//
// LED status:
//   LD4 (led[0]) = always ON  (FPGA alive)
//   LD5 (led[1]) = blinks 200ms when sending start command to LiDAR
//   LD6 (led[2]) = solid ON once LiDAR is running and streaming
//   LD7 (led[3]) = emergency stop active

module top (
    input  logic clk,
    input  logic rst_btn,     // D9 — BTN0, active HIGH (press = reset)

    input  logic lidar_rx,    // G13 — from LiDAR (yellow wire)
    output logic lidar_tx,    // B11 — to   LiDAR (green  wire)

    output logic arduino_tx,  // E15 — to Arduino Serial1 RX (pin 19)
    input  logic arduino_rx,  // E16 — from Arduino (via 1k+2k divider)

    output logic debug_tx,    // A9  — USB-UART bridge → forwards LiDAR bytes to PC

    output logic [3:0] led
);

    // Active-low reset: button not pressed (D9=0) → rst_n=1 → running
    //                   button pressed     (D9=1) → rst_n=0 → reset
    logic rst_n;
    assign rst_n = ~rst_btn;

    // ---------------------------------------------------------------
    // LiDAR UART RX (460800 baud) — receives data from LiDAR
    // ---------------------------------------------------------------
    logic [7:0] lidar_rx_data;
    logic       lidar_rx_valid;

    uart_rx #(.CLK_FREQ(100_000_000), .BAUD_RATE(460_800)) u_lidar_rx (
        .clk   (clk), .rst_n(rst_n),
        .rx    (lidar_rx),
        .data  (lidar_rx_data),
        .valid (lidar_rx_valid)
    );

    // ---------------------------------------------------------------
    // LiDAR UART TX (460800 baud) — sends commands to LiDAR
    // ---------------------------------------------------------------
    logic [7:0] lidar_tx_data;
    logic       lidar_tx_send;
    logic       lidar_tx_busy;

    uart_tx #(.CLK_FREQ(100_000_000), .BAUD_RATE(460_800)) u_lidar_tx (
        .clk   (clk), .rst_n(rst_n),
        .data  (lidar_tx_data),
        .send  (lidar_tx_send),
        .tx    (lidar_tx),
        .busy  (lidar_tx_busy)
    );

    // ---------------------------------------------------------------
    // RPLidar controller
    // ---------------------------------------------------------------
    logic       lidar_running;
    logic       send_pulse;
    logic [7:0] scan_byte;
    logic       scan_valid;

    rplidar_ctrl #(.CLK_FREQ(100_000_000)) u_ctrl (
        .clk        (clk), .rst_n(rst_n),
        .tx_data    (lidar_tx_data),
        .tx_send    (lidar_tx_send),
        .tx_busy    (lidar_tx_busy),
        .rx_data    (lidar_rx_data),
        .rx_valid   (lidar_rx_valid),
        .running    (lidar_running),
        .send_pulse (send_pulse),
        .scan_byte  (scan_byte),
        .scan_valid (scan_valid)
    );

    // ---------------------------------------------------------------
    // Parser, aggregator, emergency stop
    // ---------------------------------------------------------------
    logic [14:0] angle_q14;
    logic [15:0] dist_q4_mm;
    logic [4:0]  sector_idx;
    logic        start_flag;
    logic        point_valid;

    rplidar_parser u_parser (
        .clk        (clk), .rst_n(rst_n),
        .scan_byte  (scan_byte),
        .scan_valid (scan_valid),
        .angle_q14  (angle_q14),
        .dist_q4_mm (dist_q4_mm),
        .sector     (sector_idx),
        .start_flag (start_flag),
        .point_valid(point_valid)
    );

    logic [15:0] avg_mm [0:17];
    logic [15:0] min_mm [0:17];
    logic        sector_valid;

    sector_aggregator u_agg (
        .clk        (clk), .rst_n(rst_n),
        .sector     (sector_idx),
        .dist_q4_mm (dist_q4_mm),
        .point_valid(point_valid),
        .start_flag (start_flag),
        .avg_mm     (avg_mm),
        .min_mm     (min_mm),
        .data_valid (sector_valid)
    );

    logic emergency_stop;
    always_comb begin
        emergency_stop = 1'b0;
        for (int i = 0; i < 18; i++)
            if (min_mm[i] != 16'd0 && min_mm[i] < 16'd150)
                emergency_stop = 1'b1;
    end

    // ---------------------------------------------------------------
    // Arduino UART TX (115200 baud) + output encoder
    // ---------------------------------------------------------------
    logic [7:0] ard_tx_data;
    logic       ard_tx_send;
    logic       ard_tx_busy;
    logic       transmitting;

    uart_tx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) u_ard_tx (
        .clk   (clk), .rst_n(rst_n),
        .data  (ard_tx_data),
        .send  (ard_tx_send),
        .tx    (arduino_tx),
        .busy  (ard_tx_busy)
    );

    output_encoder #(.CLK_FREQ(100_000_000)) u_enc (
        .clk           (clk), .rst_n(rst_n),
        .avg_mm        (avg_mm),
        .min_mm        (min_mm),
        .data_valid    (sector_valid),
        .emergency_stop(emergency_stop),
        .tx_data       (ard_tx_data),
        .tx_send       (ard_tx_send),
        .tx_busy       (ard_tx_busy),
        .transmitting  (transmitting)
    );

    // ---------------------------------------------------------------
    // Debug UART (115200 baud → USB-UART bridge → /dev/ttyUSB1 on PC)
    // Forwards raw bytes received from LiDAR so PC can verify data flow.
    // ---------------------------------------------------------------
    logic [7:0] dbg_tx_data;
    logic       dbg_tx_send;
    logic       dbg_tx_busy;

    uart_tx #(.CLK_FREQ(100_000_000), .BAUD_RATE(115_200)) u_dbg_tx (
        .clk   (clk), .rst_n(rst_n),
        .data  (dbg_tx_data),
        .send  (dbg_tx_send),
        .tx    (debug_tx),
        .busy  (dbg_tx_busy)
    );

    // Forward LiDAR RX bytes to debug UART (drop if busy)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dbg_tx_data <= '0;
            dbg_tx_send <= 1'b0;
        end else begin
            dbg_tx_send <= 1'b0;
            if (lidar_rx_valid && !dbg_tx_busy) begin
                dbg_tx_data <= lidar_rx_data;
                dbg_tx_send <= 1'b1;
            end
        end
    end

    // ---------------------------------------------------------------
    // Unused input suppress
    // ---------------------------------------------------------------
    (* keep = "true" *) logic _tie_ard_rx;
    assign _tie_ard_rx = arduino_rx;

    // ---------------------------------------------------------------
    // LEDs
    // LD4 = led[0] = always ON
    // LD5 = led[1] = 200ms pulse when sending start command to LiDAR
    // LD6 = led[2] = solid ON when LiDAR running and streaming data
    // LD7 = led[3] = emergency stop
    // ---------------------------------------------------------------
    assign led[0] = 1'b1;
    assign led[1] = send_pulse;
    assign led[2] = lidar_running;
    assign led[3] = emergency_stop;

endmodule
