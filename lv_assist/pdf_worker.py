"""Isolated paged HTML renderer; the parent validates and publishes its output."""

import sys


def main():
    from weasyprint import HTML

    HTML(filename=sys.argv[1]).write_pdf(sys.argv[2])


if __name__ == '__main__':
    main()
