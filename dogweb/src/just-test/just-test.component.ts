import {Component, ElementRef, ViewChild} from '@angular/core';
import {Button} from 'primeng/button';

@Component({
  selector: 'app-just-test',
  standalone: true,
  imports: [Button],
  templateUrl: './just-test.component.html',
  styleUrl: './just-test.component.css'
})
export class JustTestComponent {
  visible: boolean = false;
  @ViewChild('leftBar') leftBar: ElementRef | null = null;

  toggleLeftBar() {
    console.log('Toggle left bar');
    if (this.leftBar) {
      this.leftBar.nativeElement.style.display = this.leftBar.nativeElement.style.display === 'none' ? 'block' : 'none';
    }
  }
}
