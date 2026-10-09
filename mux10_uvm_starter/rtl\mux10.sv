`timescale 1ns/1ps

// Example DUT: ten independent 2:1 mux lanes.
// Replace this module or its instance hookup with your actual DUT.
module mux10 (
    input  logic [9:0] a,
    input  logic [9:0] b,
    input  logic [9:0] sel,
    output logic [9:0] y
);
    assign y = sel ? b : a;
endmodule
