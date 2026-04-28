module counter_4bit (
    input wire clk,       // Clock signal
    input wire reset,     // Reset signal
    output reg [3:0] count // 4-bit counter output
);

    // Always block triggered on the positive edge of the clock or reset
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count <= 4'b0000; // Reset the counter to 0
        end else begin
            count <= count + 1; // Increment the counter
        end
    end

endmodule
