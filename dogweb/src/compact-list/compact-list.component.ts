import {Component, inject, signal} from '@angular/core';
import {DataView} from 'primeng/dataview';
import {Product} from '../domain/product';
import {Button} from 'primeng/button';
import {Tag} from 'primeng/tag';
import {ProductService} from '../service/productservice';
import {CommonModule, NgClass} from '@angular/common';

@Component({
  selector: 'app-compact-list',
  imports: [
    CommonModule,
    DataView,
    Button,
    Tag,
    NgClass
  ],
  templateUrl: './compact-list.component.html',
  styleUrl: './compact-list.component.css'
})
export class CompactListComponent {
  products = signal<any>([]);

  productService = inject(ProductService);

  ngOnInit() {
    this.productService.getProducts().then((data) => {
      const d = data.slice(0, 5);
      this.products.set([...d])
    });
  }

  getSeverity(product: Product) {
    switch (product.inventoryStatus) {
      case 'INSTOCK':
        return 'success';

      case 'LOWSTOCK':
        return 'warn';

      case 'OUTOFSTOCK':
        return 'danger';

      default:
        return null;
    }
  }
}
