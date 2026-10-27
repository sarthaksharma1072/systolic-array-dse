`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// tb_conv.v -- the im2col integration test (R3 x R1/R2)
//
// Runs a real PyTorch convolution layer through the systolic array:
// R3 quantised the layer to 8 bits and reshaped it with im2col into
// A (14x16) @ B (16x16) = C (14x16). The array must reproduce C exactly.
//
// Shapes come from im2col_metadata.json:
//   N = 16, M = 14, WIDTH = 8, ACCW = 32, weight stationary (DATAFLOW = 1)
//   A padded [14,16]   B padded [16,16]   C padded [14,16]
//   the real convolution output is the top-left 14 x 4 block of C
//////////////////////////////////////////////////////////////////////////////
 
module tb_conv;
 
    localparam N        = 16;
    localparam M        = 14;
    localparam WIDTH    = 8;
    localparam ACCW     = 32;
    localparam DATAFLOW = 1;    // B is the weight matrix -> weight stationary
    localparam VALID_C  = 4;    // real output columns, the rest is padding
 
    reg                     clk = 0, rst = 1, start = 0;
    reg                     we_a = 0, we_b = 0;
    reg  [15:0]             addr_a = 0, addr_b = 0, addr_c = 0;
    reg  signed [WIDTH-1:0] data_a = 0, data_b = 0;
    wire signed [ACCW-1:0]  data_c;
    wire                    done;
 
    always #5 clk = ~clk;       // 100 MHz
 
    top #(.N(N), .M(M), .WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(DATAFLOW)) dut (
        .clk(clk), .rst(rst), .start(start),
        .we_a(we_a), .addr_a(addr_a), .data_a(data_a),
        .we_b(we_b), .addr_b(addr_b), .data_b(data_b),
        .addr_c(addr_c), .data_c(data_c), .done(done));
 
    reg signed [WIDTH-1:0] A [0:M*N-1];
    reg signed [WIDTH-1:0] B [0:N*N-1];
    reg signed [ACCW-1:0]  C [0:M*N-1];
 
    integer i, r, c, errors, valid_errors;
 
    initial begin
        $readmemh("C:/Users/ROG/systolic_array/stim/A_conv.hex", A);
        $readmemh("C:/Users/ROG/systolic_array/stim/B_conv.hex", B);
        $readmemh("C:/Users/ROG/systolic_array/stim/C_conv.hex", C);
 
        repeat (4) @(posedge clk);
        rst = 0;
        @(posedge clk);
 
        // ---- load the im2col activation matrix
        for (i = 0; i < M*N; i = i + 1) begin
            @(negedge clk); we_a = 1; addr_a = i; data_a = A[i];
        end
        @(negedge clk); we_a = 0;
 
        // ---- load the weight matrix
        for (i = 0; i < N*N; i = i + 1) begin
            @(negedge clk); we_b = 1; addr_b = i; data_b = B[i];
        end
        @(negedge clk); we_b = 0;
 
        // ---- run one GEMM
        @(negedge clk); start = 1;
        @(negedge clk); start = 0;
        wait (done);
        @(posedge clk);
 
        // ---- compare every element against the PyTorch-derived golden file
        errors = 0; valid_errors = 0;
        for (r = 0; r < M; r = r + 1)
            for (c = 0; c < N; c = c + 1) begin
                @(negedge clk); addr_c = r*N + c;
                @(negedge clk);
                if (data_c !== C[r*N + c]) begin
                    errors = errors + 1;
                    if (c < VALID_C) valid_errors = valid_errors + 1;
                    if (errors <= 10)
                        $display("MISMATCH  C[%0d][%0d]  got %0d  want %0d",
                                 r, c, data_c, C[r*N + c]);
                end
            end
 
        $display("");
        $display("=====================================================");
        $display(" im2col integration test   N=%0d  M=%0d  WIDTH=%0d  WS",
                 N, M, WIDTH);
        $display(" full padded matrix : %0d of %0d elements wrong",
                 errors, M*N);
        $display(" real conv output   : %0d of %0d elements wrong  (%0dx%0d)",
                 valid_errors, M*VALID_C, M, VALID_C);
        if (errors == 0)
            $display(" RESULT: PASS -- the array reproduces the PyTorch convolution exactly");
        else
            $display(" RESULT: FAIL");
        $display("=====================================================");
        $finish;
    end
 
endmodule
