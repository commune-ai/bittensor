#!/bin/python3
# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
""" Benchmarking pytest fixture.

Example:
    $ python3 -m pytest -s benchmarks/template_miner.py --nucleus.nhid 600

"""
import sys
import os
import pandas
import signal
import bittensor
import time
import argparse
import multiprocessing
import bittensor
from rich.console import Console
from rich.progress import track

# Turns off console output.
bittensor.turn_console_off()


class QueryBenchmark:
    r""" Benchmark super class.
    """

    def __init__(self):
        r""" Start up benchmark background processes.
        """
        bittensor.subtensor.kill_global_mock_process()
        self.conf = QueryBenchmark.benchmark_config()
        bittensor.logging( config = self.conf )
        self.subtensor = bittensor.subtensor.mock()
        self.graph = bittensor.metagraph( subtensor = self.subtensor )
        self.wallet = bittensor.wallet.mock()
        self.dendrite = bittensor.dendrite( wallet = self.wallet, multiprocess = False )
        self.console = Console()
        self.log_dir = os.path.expanduser('{}/{}/{}/{}/{}'.format( os.path.dirname(os.path.realpath(__file__)), '/results/', 'mock', 'default', self.miner_name() ))
        self.console.log( 'Logging to: [bold blue]{}[/bold blue]'.format( self.log_dir ) )
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    @classmethod   
    def benchmark_config(cls) -> 'bittensor.Config':
        """ Get config from the argument parser
        """
        parser = argparse.ArgumentParser()
        cls.add_args( parser = parser )
        return bittensor.config( parser )

    @classmethod   
    def add_args( cls, parser: argparse.ArgumentParser ):
        try:
            parser.add_argument('--n_calls', type=int, help='Number of function calls.', default=100)
            parser.add_argument('--batch_size', type=int, help='Batch size', default=10)
            parser.add_argument('--block_size', type=int, help='Block_size', default=10)
            parser.add_argument('--delay', type=int, help='Message delay', default=0)
        except argparse.ArgumentError:
            # re-parsing arguments.
            pass
        bittensor.logging.add_args( parser )

    @classmethod   
    def help(cls):
        """ Print help to stdout
        """
        parser = argparse.ArgumentParser()
        cls.add_args( parser )
        print (cls.__new__.__doc__)
        parser.print_help()

    @staticmethod
    def miner_name() -> str:
        r""" Return miner name
        """
        raise NotImplementedError

    @staticmethod
    def run_neuron( config ):
        r""" To be implemented in the subclass, runs the neuron.
            Args:
                config (bittensor.Config)
                    Run config
        """
        raise NotImplementedError

    @staticmethod
    def config() -> 'bittensor.Config':
        r""" Return config
            Returns:
                config (bittensor.Config)
                    Run config.
        """
        raise NotImplementedError

    @staticmethod
    def _run_background_process( run_neuron_func, config_func):
        r""" Pulls the config and starts the subclass static run method.
            Args:
                run_neuron_func (Callable):
                    function which runs neuron.
                config_func (Callable):
                    function which returns neuron config.
        """
        config = config_func()
        config.wallet.name = 'mock'
        config.subtensor.network = 'mock'
        config.dataset._mock = True
        config.logging.record_log = True
        config.logging.logging_dir = 'benchmarks/results/'
        if not config.logging.debug:
            sys.stdout = open(os.devnull, 'w')
        run_neuron_func ( config )

    def startup(self):
        r""" Starts mining process.
        """
        self.process = multiprocessing.Process( target=QueryBenchmark._run_background_process, args=(self.run_neuron, self.config))
        self.process.daemon = True
        self.process.start()
        self.process.pid

    def shutdown(self):
        r""" Terminates the mining process.
        """
        try:
            os.kill(self.process.pid, signal.SIGINT)
            self.process.join( 3 )
        except:
            pass

    def __del__(self):
        r""" Tear down benchmark background processes.
        """
        self.shutdown()

    def find_endpoint(self):
        r""" Finds the background neuron axon endpoint from the chain.
            Returns:
                endpoint (bittensor.Endpoint)
                    endpoint to query for background process.
        """
        start_time = time.time()
        with self.console.status("Starting miner ..."):
            while True:
                if self.wallet.hotkey.ss58_address in self.graph.hotkeys:
                    endpoint = self.graph.endpoint_objs[ self.graph.hotkeys.index( self.wallet.hotkey.ss58_address ) ]
                    if endpoint.ip != '0.0.0.0':
                        break
                if time.time() - start_time > 100 * bittensor.__blocktime__:
                    print ( 'Failed to make connection to miner, check logs by passing flag --logging.debug')
                    sys.exit()
                self.graph.sync()
                time.sleep(bittensor.__blocktime__)
                
        self.endpoint = endpoint

    def query_sequence( self, ncalls:int, batch_size:int, block_size:int ) -> pandas.DataFrame:
        r""" Queries the background neuron with passed parameters
            Args:
                ncalls (int):
                    Number of sequential calls made.
                batch_size (int):
                    Batch size for each request.
                block_size (int):
                    Sequence length.
            Returns:
                history (List[Dict[int, float, int, float)]
                    (n, query_length, code, query_time) tuple
        """
        dataset = bittensor.dataset( _mock = True, batch_size = batch_size, block_size = block_size )
        results = []
        start_time = time.time()
        self.console.log( 'Running:\n\tqueries: {}\n\tbatch size: {}\n\tblock_length: {}'.format( str(ncalls).ljust(20), str(batch_size).ljust(20), str(block_size).ljust(20)  ) )
        for i in  track(range(ncalls), description="Querying endpoint..."):
            _, codes, qtime = self.dendrite.forward_text( 
                endpoints = self.endpoint, 
                inputs = next( dataset ) 
            )
            results.append( [ qtime.item(), codes.item(), time.time() - start_time ])
            time.sleep( self.conf.delay )
        dataframe = pandas.DataFrame( data = results, columns = ['time', 'code', 'elapsed'] )
        return dataframe

    def print_query_analysis( self, history ):
        r""" Prints analysis from the query trial.
        """
        self.console.print( '\tQPS:\t [bold blue]{}[/bold blue]'.format( str(1/history['time'].mean()).ljust(20) ))
        self.console.print( '\tSuccess:\t [bold blue]{}[/bold blue]'.format( str(  len(history[history.code == 1])/len(history) ).ljust(20) ))
        print( history.describe() )

    def run_standard_benchmark(self):
        r""" Tests default query sizes
        """
        history = self.query_sequence( ncalls = self.conf.n_calls, batch_size = self.conf.batch_size, block_size = self.conf.block_size )
        self.print_query_analysis( history )
        history.to_csv( self.log_dir + '/queries.csv' )

    def run(self):
        r""" Runs all funcs with benchmark_ prefix.
        """
        self.startup()
        self.find_endpoint()
        self.run_standard_benchmark()
        for func in dir(self):
            if callable(getattr(self, func)) and func.startswith("benchmark_"):
                self.console.log('\nRunning benchmark: [bold blue]{}[/bold blue]'.format(func))
                eval('self.' + func + "()")
                self.console.log('Done\n')
        self.shutdown()

        

