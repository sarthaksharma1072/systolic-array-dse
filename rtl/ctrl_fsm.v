`timescale 1ns / 1ps

module ctrl_fsm #(
    parameter N        = 4,
    parameter M        = 4,
    parameter DATAFLOW = 1
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output wire        load_w,
    output wire        en,
    output wire        capture,
    output reg  [15:0] t,
    output wire        done
);
    localparam IDLE = 2'd0, LOADW = 2'd1, STREAM = 2'd2, FIN = 2'd3;
    localparam TOT  = M + 2*N + 4;

    reg [1:0] state;

    assign load_w  = (state == LOADW);
    assign en      = (state == STREAM);
    assign capture = (state == STREAM);
    assign done    = (state == FIN);

    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            t     <= 16'd0;
        end else begin
            case (state)
                IDLE: begin
                    t <= 16'd0;
                    if (start) state <= (DATAFLOW == 1) ? LOADW : STREAM;
                end
                LOADW:  state <= STREAM;
                STREAM: begin
                    t <= t + 16'd1;
                    if (t == TOT-1) state <= FIN;
                end
                FIN:    state <= IDLE;
            endcase
        end
    end
endmodule