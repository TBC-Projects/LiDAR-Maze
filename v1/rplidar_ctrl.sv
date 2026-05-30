// RPLidar C1 init controller
// Sends 0xA5 0x20 (legacy scan command) to start LiDAR scanning.
// Motor on C1 starts automatically with this command.
// Retries every ~1 second if no response received.
// Outputs a 200ms "sending" pulse on send_pulse for LED visibility.

module rplidar_ctrl #(
    parameter CLK_FREQ = 100_000_000
)(
    input  logic clk,
    input  logic rst_n,

    // UART TX to lidar (460800 baud)
    output logic [7:0] tx_data,
    output logic       tx_send,
    input  logic       tx_busy,

    // UART RX from lidar (460800 baud)
    input  logic [7:0] rx_data,
    input  logic       rx_valid,

    // Status
    output logic       running,     // high once lidar is streaming
    output logic       send_pulse,  // 200ms pulse when sending start command
    output logic [7:0] scan_byte,
    output logic       scan_valid
);

    // 200ms startup delay = 20,000,000 cycles
    localparam STARTUP_CYCLES = CLK_FREQ / 5;
    // 800ms retry timeout = 80,000,000 cycles
    localparam TIMEOUT_CYCLES = (CLK_FREQ / 10) * 8;
    // 200ms LED pulse = 20,000,000 cycles
    localparam PULSE_CYCLES   = CLK_FREQ / 5;

    typedef enum logic [3:0] {
        WAIT_BOOT,
        PULSE_ON,    // hold send_pulse high 200ms before transmitting
        SEND_CMD1,
        WAIT_CMD1,
        SEND_CMD2,
        WAIT_CMD2,
        SKIP_RESP,
        RUNNING_ST
    } state_t;

    state_t      state;
    logic [27:0] cnt;
    logic [2:0]  resp_cnt;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= WAIT_BOOT;
            cnt        <= '0;
            resp_cnt   <= '0;
            running    <= 1'b0;
            send_pulse <= 1'b0;
            tx_data    <= '0;
            tx_send    <= 1'b0;
            scan_byte  <= '0;
            scan_valid <= 1'b0;
        end else begin
            tx_send    <= 1'b0;
            scan_valid <= 1'b0;

            case (state)
                // -----------------------------------------------
                WAIT_BOOT: begin
                    // 200ms delay for LiDAR power-up
                    if (cnt == STARTUP_CYCLES[27:0] - 1) begin
                        cnt        <= '0;
                        send_pulse <= 1'b1;
                        state      <= PULSE_ON;
                    end else begin
                        cnt <= cnt + 1;
                    end
                end

                // -----------------------------------------------
                // Hold LED on 200ms so it's visibly detectable
                PULSE_ON: begin
                    if (cnt == PULSE_CYCLES[27:0] - 1) begin
                        cnt   <= '0;
                        state <= SEND_CMD1;
                    end else begin
                        cnt <= cnt + 1;
                    end
                end

                // -----------------------------------------------
                SEND_CMD1: begin
                    if (!tx_busy) begin
                        tx_data <= 8'hA5;
                        tx_send <= 1'b1;
                        state   <= WAIT_CMD1;
                    end
                end

                WAIT_CMD1: begin
                    // Extra cycle so tx_busy asserts before SEND_CMD2 checks it
                    state <= SEND_CMD2;
                end

                // -----------------------------------------------
                SEND_CMD2: begin
                    if (!tx_busy) begin
                        tx_data    <= 8'h20;
                        tx_send    <= 1'b1;
                        resp_cnt   <= 3'd0;
                        send_pulse <= 1'b0;
                        state      <= WAIT_CMD2;
                    end
                end

                WAIT_CMD2: begin
                    cnt   <= '0;
                    state <= SKIP_RESP;
                end

                // -----------------------------------------------
                // Wait for 7-byte response descriptor
                // Retry after 800ms if no response
                SKIP_RESP: begin
                    cnt <= cnt + 1;

                    if (rx_valid) begin
                        cnt <= '0;  // reset timeout on activity
                        if (resp_cnt == 3'd6) begin
                            running <= 1'b1;
                            state   <= RUNNING_ST;
                        end else begin
                            resp_cnt <= resp_cnt + 1;
                        end
                    end else if (cnt == TIMEOUT_CYCLES[27:0] - 1) begin
                        // Retry
                        cnt      <= '0;
                        resp_cnt <= '0;
                        state    <= PULSE_ON;
                        send_pulse <= 1'b1;
                    end
                end

                // -----------------------------------------------
                RUNNING_ST: begin
                    if (rx_valid) begin
                        scan_byte  <= rx_data;
                        scan_valid <= 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
