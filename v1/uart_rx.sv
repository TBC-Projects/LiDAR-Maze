// Parameterized UART receiver
// CLK_FREQ / BAUD_RATE must equal the divisor
// 8N1 format, samples at mid-bit

module uart_rx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 460_800
)(
    input  logic clk,
    input  logic rst_n,
    input  logic rx,
    output logic [7:0] data,
    output logic       valid   // pulses 1 cycle when data is ready
);

    localparam DIVISOR    = CLK_FREQ / BAUD_RATE;      // cycles per bit
    localparam HALF_DIV   = DIVISOR / 2;               // sample point offset

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
    state_t state;

    logic [$clog2(DIVISOR)-1:0] baud_cnt;
    logic [2:0] bit_idx;
    logic [7:0] shift_reg;
    logic rx_sync0, rx_sync1;  // 2-FF synchronizer for metastability

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_sync0 <= 1'b1;
            rx_sync1 <= 1'b1;
        end else begin
            rx_sync0 <= rx;
            rx_sync1 <= rx_sync0;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            baud_cnt <= '0;
            bit_idx  <= '0;
            shift_reg<= '0;
            data     <= '0;
            valid    <= 1'b0;
        end else begin
            valid <= 1'b0;  // default: not valid

            case (state)
                IDLE: begin
                    if (!rx_sync1) begin  // falling edge = start bit
                        baud_cnt <= HALF_DIV[($clog2(DIVISOR)-1):0];  // offset to sample mid-bit
                        state    <= START;
                    end
                end

                START: begin
                    if (baud_cnt == '0) begin
                        // sample middle of start bit
                        if (!rx_sync1) begin
                            // valid start bit
                            baud_cnt <= DIVISOR - 1;
                            bit_idx  <= 3'd0;
                            state    <= DATA;
                        end else begin
                            state <= IDLE;  // false start
                        end
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end

                DATA: begin
                    if (baud_cnt == '0) begin
                        shift_reg <= {rx_sync1, shift_reg[7:1]};  // LSB first
                        baud_cnt  <= DIVISOR - 1;
                        if (bit_idx == 3'd7) begin
                            state <= STOP;
                        end else begin
                            bit_idx <= bit_idx + 1;
                        end
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end

                STOP: begin
                    if (baud_cnt == '0) begin
                        if (rx_sync1) begin  // valid stop bit
                            data  <= shift_reg;
                            valid <= 1'b1;
                        end
                        state <= IDLE;
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end
            endcase
        end
    end

endmodule
