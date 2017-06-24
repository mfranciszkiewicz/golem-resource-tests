import click
import stun

from monitor.monitor import Monitor
from resources.dat.logic import DatServerSession, DatClientSession
from resources.ipfs.logic import IPFSClientSession, IPFSServerSession


@click.command()
@click.argument('name')
@click.argument('address')
@click.option('--client', '-c', is_flag=True, default=False,
              help='Work in client mode')
@click.option('--proxy-client', '-pc', nargs=1, default=None,
              help='Request a proxy connection for node (by name)')
@click.option('--server', '-s', is_flag=True, default=False,
              help='Work in server mode')
@click.option('--proxy-server', '-ps', is_flag=True, default=False,
              help='Work in proxy server mode')
@click.option('--output_dir', '-o', nargs=1, default='downloads',
              help='Set output directory')
@click.option('--log_dir', '-l', nargs=1, default='logs',
              help='Set log directory')
@click.option('--tasks', '-t', nargs=1, default=10,
              help='Number of tasks to simulate (client only)')
@click.option('--size', '-sz', nargs=1, default=10,
              help='Generated file size [MB]')
@click.option('--timeout', '-to', nargs=1, default=120,
              help='Download timeout')
@click.option('--stun-test', '-st', is_flag=True, default=False,
              help='Perform a STUN test')
@click.option('--ipfs', is_flag=True, default=False,
              help='IPFS')
@click.option('--dat', is_flag=True, default=False,
              help='Dat')
@click.option('--connect', is_flag=True, default=False)
def main(name, address, client, proxy_client, server, proxy_server, output_dir, log_dir,
         tasks, size, timeout, stun_test, ipfs, dat, connect):

    assert (ipfs or dat) and not (ipfs and dat), "Please specify the IPFS or Dat flag"

    if client or proxy_client:

        if ipfs:
            cls = IPFSClientSession
        else:
            cls = DatClientSession

        if proxy_client:
            proxy_client = (address, proxy_client)

        logic = cls(name, address,
                    output_dir, log_dir,
                    int(tasks), int(size),
                    proxy=proxy_client, connect=connect)

    elif server or proxy_server:

        if ipfs:
            cls = IPFSServerSession
        else:
            cls = DatServerSession

        if proxy_server:
            proxy_server = (address, None)

        logic = cls(name, address,
                    output_dir, log_dir,
                    int(size),
                    proxy=proxy_server, connect=connect)

    else:
        raise RuntimeError("Neither (proxy) client or (proxy) server mode specified")

    if stun_test:
        perform_stun_test()

    session = Monitor(logic, timeout=int(timeout))
    session.start()


def perform_stun_test():
    nat_type, external_ip, external_port = stun.get_ip_info(
        source_ip=stun.DEFAULTS['source_ip'],
        source_port=stun.DEFAULTS['source_port'],
        stun_host=None,
        stun_port=stun.DEFAULTS['stun_port']
    )

    print('NAT Type:', nat_type)
    print('External IP:', external_ip)
    print('External Port:', external_port)


if __name__ == '__main__':
    main()
