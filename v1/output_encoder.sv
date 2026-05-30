// Output encoder: transmits 77-byte binary frame to Arduino at up to 10 Hz.
//
// Frame format:
//   [0]     0xAA  header
//   [1]     0x55  header
//   [2]     emergency_stop (0x00 or 0x01)
//   [3]     0x00  reserved
//   [4..75] 18 sectors × 4 bytes: avg_hi, avg_lo, min_hi, min_lo (big-endian mm)
//   [76]    XOR checksum of bytes [2..75]

module output_encoder #(
    parameter CLK_FREQ = 100_000_000
)(
    input  logic        clk,
    input  logic        rst_n,

    input  logic [15:0] avg_mm [0:17],
    input  logic [15:0] min_mm [0:17],
    input  logic        data_valid,
    input  logic        emergency_stop,

    output logic [7:0]  tx_data,
    output logic        tx_send,
    input  logic        tx_busy,

    output logic        transmitting
);

    localparam FRAME_LEN = 77;
    localparam THROTTLE  = CLK_FREQ / 10;  // 10 Hz max

    logic [7:0]  frame [0:FRAME_LEN-1];
    logic [6:0]  byte_idx;

    typedef enum logic [2:0] {
        IDLE,
        BUILD_HDR,
        BUILD_DATA,
        BUILD_CSUM,
        SEND,
        WAIT_TX
    } state_t;
    state_t state;

    logic [23:0] throttle_cnt;
    logic        throttle_ok;
    logic        pending;

    // Snapshots (captured when data_valid pulses)
    logic [15:0] snap_avg [0:17];
    logic [15:0] snap_min [0:17];
    logic        snap_estop;

    logic [7:0]  csum_acc;
    logic [4:0]  build_sect;

    integer i;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= IDLE;
            byte_idx     <= '0;
            tx_send      <= 1'b0;
            transmitting <= 1'b0;
            throttle_cnt <= '0;
            throttle_ok  <= 1'b0;
            pending      <= 1'b0;
            snap_estop   <= 1'b0;
            csum_acc     <= '0;
            build_sect   <= '0;
            for (i = 0; i < 18; i++) begin
                snap_avg[i] <= '0;
                snap_min[i] <= '0;
            end
            for (i = 0; i < FRAME_LEN; i++) frame[i] <= '0;
        end else begin
            tx_send <= 1'b0;

            // Throttle token (regenerates every 100ms)
            if (throttle_cnt == THROTTLE[23:0] - 1) begin
                throttle_cnt <= '0;
                throttle_ok  <= 1'b1;
            end else begin
                throttle_cnt <= throttle_cnt + 1;
            end

            // Capture snapshot
            if (data_valid) begin
                for (i = 0; i < 18; i++) begin
                    snap_avg[i] <= avg_mm[i];
                    snap_min[i] <= min_mm[i];
                end
                snap_estop <= emergency_stop;
                pending    <= 1'b1;
            end

            case (state)
                IDLE: begin
                    transmitting <= 1'b0;
                    if (pending && throttle_ok) begin
                        pending      <= 1'b0;
                        throttle_ok  <= 1'b0;
                        transmitting <= 1'b1;
                        state        <= BUILD_HDR;
                    end
                end

                BUILD_HDR: begin
                    frame[0] <= 8'hAA;
                    frame[1] <= 8'h55;
                    frame[2] <= snap_estop ? 8'h01 : 8'h00;
                    frame[3] <= 8'h00;
                    csum_acc   <= snap_estop ? 8'h01 : 8'h00;
                    build_sect <= 5'd0;
                    state      <= BUILD_DATA;
                end

                // One sector per clock cycle — no 'automatic' variables needed
                BUILD_DATA: begin
                    frame[4 + {2'b0, build_sect} * 4 + 0] <= snap_avg[build_sect][15:8];
                    frame[4 + {2'b0, build_sect} * 4 + 1] <= snap_avg[build_sect][7:0];
                    frame[4 + {2'b0, build_sect} * 4 + 2] <= snap_min[build_sect][15:8];
                    frame[4 + {2'b0, build_sect} * 4 + 3] <= snap_min[build_sect][7:0];
                    csum_acc <= csum_acc
                                ^ snap_avg[build_sect][15:8]
                                ^ snap_avg[build_sect][7:0]
                                ^ snap_min[build_sect][15:8]
                                ^ snap_min[build_sect][7:0];

                    if (build_sect == 5'd17)
                        state <= BUILD_CSUM;
                    else
                        build_sect <= build_sect + 1;
                end

                BUILD_CSUM: begin
                    frame[76] <= csum_acc;
                    byte_idx  <= 7'd0;
                    state     <= SEND;
                end

                SEND: begin
                    if (!tx_busy) begin
                        tx_data <= frame[byte_idx];
                        tx_send <= 1'b1;
                        state   <= WAIT_TX;
                    end
                end

                WAIT_TX: begin
                    if (!tx_busy) begin
                        if (byte_idx == FRAME_LEN - 1)
                            state <= IDLE;
                        else begin
                            byte_idx <= byte_idx + 1;
                            state    <= SEND;
                        end
                    end
                end
            endcase
        end
    end

endmodule
