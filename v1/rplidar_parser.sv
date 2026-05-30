// RPLidar C1 legacy scan (0x20) 5-byte node parser
//
// Node format (byte indices 0..4):
//   byte0: {quality[7:2], check_bit[1], start[0]}
//          valid if byte0[1] == ~byte0[0]
//   byte1: {angle_q6[6:0], must_be_1}
//          valid if byte1[0] == 1
//   byte2: {1'b0, angle_q6[13:7]}
//   byte3: dist_q2[7:0]
//   byte4: dist_q2[15:8]
//
// angle_q6 is 14 bits; max = 360*64 = 23040 → fits in 15 bits

module rplidar_parser (
    input  logic       clk,
    input  logic       rst_n,

    input  logic [7:0] scan_byte,
    input  logic       scan_valid,

    output logic [14:0] angle_q14,    // angle in 1/64-degree units (15-bit)
    output logic [15:0] dist_q4_mm,   // distance in 1/4-mm units
    output logic [4:0]  sector,       // 0..17
    output logic        start_flag,
    output logic        point_valid
);

    logic [2:0]  byte_cnt;
    logic [7:0]  rx_buf [0:4];   // renamed from 'buf' (reserved keyword)

    logic [14:0] angle_raw;
    logic [15:0] dist_raw;

    assign angle_raw = {rx_buf[2][6:0], rx_buf[1][7:1]};  // 14-bit field in 15-bit wire
    assign dist_raw  = {rx_buf[4], rx_buf[3]};

    // Sector decode: floor(angle_deg / 20) = floor(angle_q14 / 1280)
    // angle_q14 range 0..23039, sector 0..17
    function automatic logic [4:0] angle_to_sector(input logic [14:0] a);
        if      (a < 15'd1280)  return 5'd0;
        else if (a < 15'd2560)  return 5'd1;
        else if (a < 15'd3840)  return 5'd2;
        else if (a < 15'd5120)  return 5'd3;
        else if (a < 15'd6400)  return 5'd4;
        else if (a < 15'd7680)  return 5'd5;
        else if (a < 15'd8960)  return 5'd6;
        else if (a < 15'd10240) return 5'd7;
        else if (a < 15'd11520) return 5'd8;
        else if (a < 15'd12800) return 5'd9;
        else if (a < 15'd14080) return 5'd10;
        else if (a < 15'd15360) return 5'd11;
        else if (a < 15'd16640) return 5'd12;
        else if (a < 15'd17920) return 5'd13;
        else if (a < 15'd19200) return 5'd14;
        else if (a < 15'd20480) return 5'd15;
        else if (a < 15'd21760) return 5'd16;
        else                    return 5'd17;
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            byte_cnt    <= '0;
            angle_q14   <= '0;
            dist_q4_mm  <= '0;
            sector      <= '0;
            start_flag  <= '0;
            point_valid <= '0;
            rx_buf[0] <= '0; rx_buf[1] <= '0; rx_buf[2] <= '0;
            rx_buf[3] <= '0; rx_buf[4] <= '0;
        end else begin
            point_valid <= 1'b0;

            if (scan_valid) begin
                if (byte_cnt == 3'd0) begin
                    // Byte 0: check_bit must equal !start
                    if (scan_byte[1] == ~scan_byte[0]) begin
                        rx_buf[0] <= scan_byte;
                        byte_cnt  <= 3'd1;
                    end
                end else if (byte_cnt == 3'd1) begin
                    if (!scan_byte[0]) begin
                        // Invalid byte1 (LSB must be 1) — resync
                        // But first check if this could be a new byte0
                        if (scan_byte[1] == ~scan_byte[0]) begin
                            rx_buf[0] <= scan_byte;
                            byte_cnt  <= 3'd1;
                        end else begin
                            byte_cnt <= 3'd0;
                        end
                    end else begin
                        rx_buf[1] <= scan_byte;
                        byte_cnt  <= 3'd2;
                    end
                end else begin
                    rx_buf[byte_cnt] <= scan_byte;
                    if (byte_cnt == 3'd4) begin
                        byte_cnt <= 3'd0;
                        // NOTE: rx_buf[4] won't update until next cycle (non-blocking),
                        // so read scan_byte directly as the distance high byte.
                        if ({scan_byte, rx_buf[3]} != 16'd0) begin
                            angle_q14   <= angle_raw;
                            dist_q4_mm  <= {scan_byte, rx_buf[3]};
                            sector      <= angle_to_sector(angle_raw);
                            start_flag  <= rx_buf[0][0];
                            point_valid <= 1'b1;
                        end
                    end else begin
                        byte_cnt <= byte_cnt + 1;
                    end
                end
            end
        end
    end

endmodule
