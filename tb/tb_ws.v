`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 22:46:29
// Design Name: 
// Module Name: tb_ws
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

module tb_ws;
    localparam N = 4, M = 4, WIDTH = 8, ACCW = 32;

    reg clk = 0, rst = 1, en = 0, load_w = 0;
    always #5 clk = ~clk;

    reg signed [WIDTH-1:0] A [0:M*N-1];
    reg signed [WIDTH-1:0] B [0:N*N-1];
    reg signed [ACCW-1:0]  C    [0:M*N-1];
    reg signed [ACCW-1:0]  Cgot [0:M*N-1];

    reg  [N*N*WIDTH-1:0] w_flat;
    reg  [N*WIDTH-1:0]   a_edge;
    reg  [N*ACCW-1:0]    v_edge;
    wire [N*N*ACCW-1:0]  acc_flat;
    wire [N*ACCW-1:0]    v_bottom;

    systolic_array #(.N(N), .WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(1)) dut (
        .clk(clk), .rst(rst), .en(en), .load_w(load_w), .w_flat(w_flat),
        .a_edge(a_edge), .v_edge(v_edge),
        .acc_flat(acc_flat), .v_bottom(v_bottom));

    integer t, i, j, r, c, idx, errors, cycles;
    reg signed [WIDTH-1:0] aw;

    initial begin
        $readmemh("C:/Users/ROG/systolic_array/stim/A.hex", A);
        $readmemh("C:/Users/ROG/systolic_array/stim/B.hex", B);
        $readmemh("C:/Users/ROG/systolic_array/stim/C.hex", C);

        for (i = 0; i < M*N; i = i + 1) Cgot[i] = 0;

        a_edge = 0; v_edge = 0; w_flat = 0;
        repeat (2) @(negedge clk);
        rst = 0;

        // preload: PE[r][c] holds B[r][c]
        for (r = 0; r < N; r = r + 1)
            for (c = 0; c < N; c = c + 1)
                w_flat[(r*N+c)*WIDTH +: WIDTH] = B[r*N + c];
        load_w = 1; en = 0;
        @(negedge clk);
        load_w = 0; en = 1;

        cycles = 0;
        for (t = 0; t < M + 2*N + 4; t = t + 1) begin
            for (r = 0; r < N; r = r + 1) begin
                aw = ((t-r) >= 0 && (t-r) < M) ? A[(t-r)*N + r] : {WIDTH{1'b0}};
                a_edge[r*WIDTH +: WIDTH] = aw;
            end
            @(negedge clk);
            cycles = cycles + 1;
            for (c = 0; c < N; c = c + 1) begin
                idx = t - N - c + 1;
                if (idx >= 0 && idx < M)
                    Cgot[idx*N + c] = v_bottom[c*ACCW +: ACCW];
            end
        end

        errors = 0;
        for (i = 0; i < M; i = i + 1)
            for (j = 0; j < N; j = j + 1)
                if (Cgot[i*N+j] !== C[i*N+j]) begin
                    $display("FAIL C[%0d][%0d] expected %0d got %0d",
                             i, j, C[i*N+j], Cgot[i*N+j]);
                    errors = errors + 1;
                end

        if (errors == 0) $display("PASS WS: all %0d outputs match, %0d cycles", M*N, cycles);
        else             $display("FAIL WS: %0d mismatches", errors);
        $finish;
    end
endmodule
