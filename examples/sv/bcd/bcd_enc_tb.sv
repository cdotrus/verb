// Testbench for the binary to decimal encoder (BCD) module.

// This interface is automatically @generated by Verb.
// It is not intended for manual editing.
interface bcd_enc_if #(
    parameter int LEN,
    parameter int DIGITS
);
    logic go;
    logic[LEN-1:0] bin;
    logic[(4*DIGITS)-1:0] bcd;
    logic done;
    logic ovfl;
endinterface

module bcd_enc_tb 
    import godan::*;
#(
    parameter int LEN = 4,
    parameter int DIGITS = 2
);

    logic clk = 1'b0;
    logic rst = 1'b0;

    localparam int TIMEOUT_LIMIT = 1_000;

    // instantiate the set of signals to communicate with the hw dut
    bcd_enc_if #(
        .LEN(LEN),
        .DIGITS(DIGITS)
    ) bfm();
    
    // instantiate the set of signals to communicate with the sw model
    bcd_enc_if #(
        .LEN(LEN),
        .DIGITS(DIGITS)
    ) mdl();

    // instantiate the device under test
    bcd_enc #(
        .LEN(LEN),
        .DIGITS(DIGITS)
    ) dut (
        .rst(rst),
        .clk(clk),
        .go(bfm.go),
        .bin(bfm.bin),
        .bcd(bfm.bcd),
        .done(bfm.done),
        .ovfl(bfm.ovfl)
    );

    // produce a clock with 50% duty cycle
    always #(20ns) clk = ~clk;

    // drive incoming transactions
    always begin: driver 
        static int inputs = $fopen("inputs.txt", "r");

        $dumpfile("tb.vcd");
        $dumpvars(0, bcd_enc_tb);

        // perform initial reset
        sync_hi_async_lo(clk, rst, 2);

        while (!$feof(inputs)) begin
            send(inputs);
            @(negedge clk);
        end
        wait(0);
    end

    // check outgoing transactions for correctness
    always begin: monitor
        static int outputs = $fopen("outputs.txt", "r");

        while (!$feof(outputs)) begin
            // wait until falling edge of done signal to check for next outputs
            observe(clk, bfm.done, 1'b0, TIMEOUT_LIMIT, "undone");
            // wait for the outgoing data to be ready
            observe(clk, bfm.done, 1'b1, TIMEOUT_LIMIT, "done");
            // compare outputs
            recv(outputs);
        end
        $finish;
    end

    // This task is automatically @generated by Verb.
    // It is not intended for manual editing.
    task send(int fd);
        automatic string line;
        if (!$feof(fd)) begin
            $fgets(line, fd);
            $sscanf(parse(line), "%b", bfm.go);
            $sscanf(parse(line), "%b", bfm.bin);
        end
    endtask

    // This task is automatically @generated by Verb.
    // It is not intended for manual editing.
    task recv(int fd);
        automatic string line;
        if (!$feof(fd)) begin
            $fgets(line, fd);
            $sscanf(parse(line), "%b", mdl.bcd);
            $sscanf(parse(line), "%b", mdl.done);
            $sscanf(parse(line), "%b", mdl.ovfl);
        end
        assert_eq(bfm.bcd, mdl.bcd, "bcd");
        assert_eq(bfm.done, mdl.done, "done");
        assert_eq(bfm.ovfl, mdl.ovfl, "ovfl");
    endtask


    // Concurrent assertion for done holding until next go is set 
    always begin: ca_done_stays_active_until_go
        logic done_stay;
        if (done_stay == 1'b1 && bfm.go == 1'b1) begin
            done_stay = 1'b0;
        end else if (bfm.go == 1'b0 && bfm.done == 1'b1) begin
            done_stay = 1'b1;
        end
        assert_stbl(clk, done_stay, 1'b1, bfm.done, "done stays high until next go");
    end

    // Concurrent assertion for BCD output maintaining answer
    always begin: ca_bcd_is_const_while_done
        assert_stbl(clk, bfm.done, 1'b1, bfm.bcd, "done's dependency bcd");
    end

    // Concurrent assertion for OVERFLOW output maintaining answer
    always begin: ca_ovfl_is_const_while_done
        assert_stbl(clk, bfm.done, 1'b1, bfm.ovfl, "done's dependency ovfl");
    end

    // Concurrent assertion for starting new processing on cycle after go
    always @(negedge clk) begin: ca_go_after_done
        #0 if (bfm.done == 1'b1 && bfm.go == 1'b1) begin
            @(negedge clk);
            assert_eq(bfm.done, 1'b0, "done after go");
        end
    end

endmodule
