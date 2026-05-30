// Parameterized UART transmitter
// 8N1 format

module uart_tx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 115_200
)(
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data,
    input  logic       send,   // pulse 1 cycle to start transmission
    output logic       tx,
    output logic       busy    // high while transmitting
);

    localparam DIVISOR = CLK_FREQ / BAUD_RATE;

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
    state_t state;

    logic [$clog2(DIVISOR)-1:0] baud_cnt;
    logic [2:0] bit_idx;
    logic [7:0] shift_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            tx       <= 1'b1;
            busy     <= 1'b0;
            baud_cnt <= '0;
            bit_idx  <= '0;
            shift_reg<= '0;
        end else begin
            case (state)
                IDLE: begin
                    tx   <= 1'b1;
                    busy <= 1'b0;
                    if (send) begin
                        shift_reg <= data;
                        baud_cnt  <= DIVISOR - 1;
                        busy      <= 1'b1;
                        state     <= START;
                    end
                end

                START: begin
                    tx <= 1'b0;  // start bit
                    if (baud_cnt == '0) begin
                        baud_cnt <= DIVISOR - 1;
                        bit_idx  <= 3'd0;
                        state    <= DATA;
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end

                DATA: begin
                    tx <= shift_reg[0];  // LSB first
                    if (baud_cnt == '0) begin
                        shift_reg <= {1'b0, shift_reg[7:1]};
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
                    tx <= 1'b1;  // stop bit
                    if (baud_cnt == '0) begin
                        state <= IDLE;
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end
            endcase
        end
    end

endmodule
