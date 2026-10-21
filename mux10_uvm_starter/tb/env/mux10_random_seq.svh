class mux10_random_seq extends uvm_sequence #(mux10_item);
        `uvm_object_utils(mux10_random_seq)
        rand int unsigned num_items;

        function new(string name = "mux10_random_seq");
            super.new(name);
            num_items = 200;
        endfunction

        virtual task body();
            mux10_item req;
            repeat (num_items) begin
                req = mux10_item::type_id::create("random_item");
                start_item(req);
                if (!req.randomize())
                    `uvm_fatal("RANDFAIL", "Could not randomize mux10_item")
                finish_item(req);
            end
        endtask
    endclass
