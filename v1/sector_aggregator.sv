// Sector aggregator — no hardware dividers.
// min_mm: exact (shift 1/4-mm units → mm)
// avg_mm: approximation via right-shift (sum >> 7 ≈ sum / 4 / ~28pts)
//         accurate to ~10% at nominal 28 points/sector; fine for navigation.
//
// On start_flag: captures previous sweep, resets accumulators, begins new sweep.

module sector_aggregator (
    input  logic        clk,
    input  logic        rst_n,

    input  logic [4:0]  sector,
    input  logic [15:0] dist_q4_mm,   // 1/4-mm units
    input  logic        point_valid,
    input  logic        start_flag,

    output logic [15:0] avg_mm  [0:17],
    output logic [15:0] min_mm  [0:17],
    output logic        data_valid
);

    // Accumulators (1/4-mm units)
    logic [31:0] acc_sum   [0:17];
    logic [15:0] acc_min   [0:17];

    logic first_sweep;

    integer i;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            first_sweep <= 1'b0;
            data_valid  <= 1'b0;
            for (i = 0; i < 18; i++) begin
                acc_sum[i]  <= '0;
                acc_min[i]  <= 16'hFFFF;
                avg_mm[i]   <= '0;
                min_mm[i]   <= '0;
            end
        end else begin
            data_valid <= 1'b0;

            if (point_valid) begin
                if (start_flag && first_sweep) begin
                    // ---- Snapshot: convert accumulators → outputs (no divider) ----
                    // avg_mm ≈ acc_sum >> 7  (sum_q4 / 128 ≈ sum_q4 / (4 * ~32pts))
                    // min_mm = acc_min >> 2  (exact: 1/4mm → mm)
                    for (i = 0; i < 18; i++) begin
                        avg_mm[i] <= (acc_sum[i] != 0) ? acc_sum[i][22:7] : 16'd0;
                        min_mm[i] <= (acc_min[i] != 16'hFFFF) ? {2'b0, acc_min[i][15:2]} : 16'd0;
                    end
                    data_valid <= 1'b1;

                    // Reset accumulators for new sweep
                    for (i = 0; i < 18; i++) begin
                        acc_sum[i] <= '0;
                        acc_min[i] <= 16'hFFFF;
                    end
                end

                if (start_flag) first_sweep <= 1'b1;

                // Accumulate this point only if it is NOT the start-of-sweep marker.
                // When start_flag is set we just snapshotted and reset accumulators above;
                // accumulating on the same cycle would race against the reset (last
                // non-blocking write wins → old sum used as base instead of 0).
                if (!start_flag && sector < 5'd18) begin
                    acc_sum[sector] <= acc_sum[sector] + dist_q4_mm;
                    if (dist_q4_mm < acc_min[sector])
                        acc_min[sector] <= dist_q4_mm;
                end
            end
        end
    end

endmodule
